import asyncio
import sys
from flask import Flask, jsonify, request
from flask_cors import CORS
import pymongo
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
from pymongo.errors import DuplicateKeyError
from bson import ObjectId
import os
import time
import traceback
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import OperationFailure

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}}, supports_credentials=True)
#for hosting
# CORS(app, resources={r"/*": {"origins": "http://54.251.76.117:5173/"}}, supports_credentials=True)
app.secret_key = "inf2002dbprojectpartone"

query_count = 0
throughput_start_time = time.time()

async def get_db_connection():
    try:
        connection_st = time.time()
        client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
        client.admin.command('ping')
        db = client[os.getenv("DATABASE_NAME")]
        connection_et = time.time()
        connection_time = connection_et - connection_st
        print(f"Database connection Time: {connection_time:.4f} seconds")
        print("MongoDB connection successful!")
        return db
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return None

async def create_indexes(db):
    await db['Users'].create_index([('username', 1)], unique=True)
    await db['Pets_Info'].create_index([('type', 1)])
    await db['Pets_Info'].create_index([('health_condition', 1)])
    await db['Pets_Info'].create_index([('sterilisation_status', 1)])

async def get_next_user_id(db, retries=3, delay=1):
    """
    Tries to get the next user ID with retry logic to handle concurrency issues
    """
    attempt = 0
    while attempt < retries:
        try:
            #Increment the userID counter in the counter collection
            counter = await db["counter"].find_one_and_update(
                {"_id": "user_id"},
                {"$inc": {"sequence_value": 1}},
                upsert=True,
                return_document=True
            )
            if not counter or 'sequence_value' not in counter:
                raise Exception("Failed to get next user ID")
            return counter["sequence_value"]
        
        except OperationFailure as e:
            print(f"Retry {attempt + 1}/{retries} due to: {e}")
            attempt += 1
            if attempt < retries:
                time.sleep(delay)
            else:
                raise Exception(f"Failed to get next user ID after {retries} retries") from e

"""
--- User Log In Endpoints ---

"""

@app.route('/api/v1/register', methods=['POST'])
async def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Missing required fields"}), 400

    hashed_password = generate_password_hash(password)
    db = await get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    user_collection = db['Users']
    
    try:
        registerSession = await db.client.start_session()
        
        retries = 3
        for _ in range(retries):
            try:
                async with registerSession.start_transaction():
                    existing_user = await user_collection.find_one({"username": username}, session=registerSession)
                    if existing_user:
                        return jsonify({"error": "Username already exists"}), 400

                    next_user_id = await get_next_user_id(db)

                    await user_collection.insert_one({
                        "user_id": next_user_id,
                        "username": username,
                        "password": hashed_password,
                        "role": "adopter"
                    }, session=registerSession)

                break
            except pymongo.errors.PyMongoError as e:
                print(f"Transaction error, retrying: {str(e)}")
                if registerSession.in_transaction:
                    await registerSession.abort_transaction()               
        else:
            return jsonify({"error": "Failed to register user after multiple attempts"}), 500

        await registerSession.commit_transaction()

        return jsonify({"message": "User registered successfully", "user_id": next_user_id}), 201

    except Exception as e:
        print(f"Error during registration: {str(e)}")
        if registerSession.in_transaction:
            await registerSession.abort_transaction()
            
        return jsonify({"error": str(e)}), 500
    
    finally:
        await registerSession.end_session()


@app.route('/api/v1/login', methods=['POST'])
async def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Missing username or password"}), 400

    db = await get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    user_collection = db['Users']
    user = await user_collection.find_one({"username": username})

    if user and check_password_hash(user['password'], password):
        return jsonify({
            "message": "Logged in successfully",
            "user": {"user_id": user['user_id'], "username": user['username'], "role": user['role']}
        }), 200
    else:
        return jsonify({"error": "Invalid username or password"}), 401


"""
--- Pets Endpoints ---
"""

#WORKING
@app.route('/api/v1/getPets', methods=['GET'])
async def get_all_pets():
    start_time = time.time()
    db = await get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    pet_info_collection = db['Pets_Info']
    pipeline = [
        {"$lookup": {
            "from": "Pet_Condition",
            "localField": "pet_condition_id",
            "foreignField": "pet_condition_id",
            "as": "condition_info"
        }},
        {"$unwind": {"path": "$condition_info", "preserveNullAndEmptyArrays": True}}
    ]
    
    query_start_time = time.time()
    pets = await pet_info_collection.aggregate(pipeline).to_list(length=None)
    query_end_time = time.time()

    query_time = query_end_time - query_start_time
    print(f"Query Time: {query_time:.4f} seconds")


    for pet in pets:
        pet['_id'] = str(pet['_id'])
        if pet.get('condition_info') and '_id' in pet['condition_info']:
            pet['condition_info']['_id'] = str(pet['condition_info']['_id'])

    end_time = time.time()
    total_time = end_time - start_time
    print(f"Total Response Time: {total_time:.4f} seconds")

    return jsonify(pets), 200

# WORKING
@app.route('/api/v1/getTop3', methods=['GET'])
async def get_top3():
    db = await get_db_connection()  

    if db is None:
        return jsonify([]), 500  

    try:
        top3_pets = await db['Pets_Info'].aggregate([ 
            {
                "$lookup": {
                    "from": "Favourites",   
                    "localField": "pet_id",      
                    "foreignField": "pet_id",    
                    "as": "favourites"          
                }
            },
            {
                "$addFields": {
                    "favourite_count": {"$size": "$favourites"} 
                }
            },
            {
                "$sort": {"favourite_count": -1} 
            },
            {
                "$limit": 3 
            },
            {
                "$project": {
                    "favourites": 0 
                }
            }
        ]).to_list(length=None)


        for pet in top3_pets:
            if '_id' in pet:
                pet['_id'] = str(pet['_id'])

        return jsonify(top3_pets), 200 

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# WORKING
@app.route('/api/v1/filterpets', methods=['POST'])
async def filter_pets():

    global query_count, throughput_start_time

    query_count += 1

    data = request.json

    # Extract search filters
    filter_type = data.get('type')
    filter_value = data.get('value')
    gender = data.get('gender')
    health_condition = data.get('health_condition')
    sterilisation_status = data.get('sterilisation_status')

    # Initialize the base match conditions
    match_conditions = {}

    # Only add filters if values are provided
    if filter_type and filter_value:
        match_conditions[filter_type] = {"$regex": filter_value, "$options": "i"}  # Case-insensitive search

    if gender:
        match_conditions["gender"] = gender

    if health_condition:
        match_conditions["condition_info.health_condition"] = health_condition

    if sterilisation_status in ["0", "1"]:
        match_conditions["condition_info.sterilisation_status"] = int(sterilisation_status)

    print("Applied Filters:", match_conditions)  # Debug log for applied filters

    db = await get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        pets_info_collection = db['Pets_Info']

        pipeline = [
            {"$lookup": {
                "from": "Pet_Condition",
                "localField": "pet_condition_id",
                "foreignField": "pet_condition_id",
                "as": "condition_info"
            }},
            {"$unwind": "$condition_info"},
            {"$match": match_conditions}
        ]

        # Fetch filtered pets
        query_start_time = time.time()
        pets = await pets_info_collection.aggregate(pipeline).to_list(length=None)
        end_time = time.time()

        query_time = end_time - query_start_time
        print(f"Query Time: {query_time:.4f} seconds")

        # Convert ObjectId fields to strings
        for pet in pets:
            for key, value in pet.items():
                if isinstance(value, ObjectId):
                    pet[key] = str(value)
            if "condition_info" in pet:
                for key, value in pet["condition_info"].items():
                    if isinstance(value, ObjectId):
                        pet["condition_info"][key] = str(value)

        
        # Calculate and display throughput every minute
        elapsed_time = time.time() - throughput_start_time
        if elapsed_time >= 60:  # Calculate throughput every 60 seconds
            qps = query_count / elapsed_time
            print(f"Query Throughput: {qps:.2f} queries per second")
            # Reset counter and start time
            query_count = 0
            throughput_start_time = time.time()

        return jsonify(pets), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# WORKING
@app.route('/api/v1/addFavourite', methods=['POST'])
async def add_favourite():
    data = request.json
    pet_id = data.get('pet_id')
    user_id = data.get('user_id')

    if not pet_id:
        return jsonify({"error": "Pet ID is required"}), 400
    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    print(f"Received user_id: {user_id} of type {type(user_id)}")

    try:
        user_id = int(user_id)  
    except ValueError:
        return jsonify({"error": "User ID must be an integer"}), 400

    db = await get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    favourites_collection = db['Favourites']
    
    try:
        existing_favourite = await favourites_collection.find_one({"user_id": user_id, "pet_id": pet_id})
        if existing_favourite:
            return jsonify({"error": "Pet is already in favourites"}), 400
        
        last_favourite = await favourites_collection.find_one(sort=[("favourite_id", -1)])
        next_favourite_id = last_favourite['favourite_id'] + 1 if last_favourite else 1


        await favourites_collection.insert_one({
            "favourite_id": next_favourite_id,
            "user_id": user_id,  
            "pet_id": pet_id
        })

        return jsonify({"message": "Pet added to favourites successfully"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


    
@app.route('/api/v1/getReservedPets', methods=['GET'])
async def get_reserved_pets():
    db = await get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    pipeline = [
        {"$lookup": {
            "from": "Applications",
            "localField": "_id",
            "foreignField": "pet_id",
            "as": "application_info"
        }},
        {"$match": {"application_info": {"$ne": []}}}  # Only include pets with applications
    ]

    pets_in_applications = await db["Pets_Info"].aggregate(pipeline).to_list(length=None)

    #Convert ObjectIds to strings for JSON compatibility
    for pet in pets_in_applications:
        pet['_id'] = str(pet['_id'])

    return jsonify(pets_in_applications), 200


# WORKING
@app.route('/api/v1/getFavourites', methods=['GET'])
async def get_favourites():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    try:
        user_id = int(user_id)
    except ValueError:
        return jsonify({"error": "Invalid user_id format"}), 400

    db = await get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$lookup": {
            "from": "Pets_Info",            
            "localField": "pet_id",         
            "foreignField": "pet_id",       
            "as": "pet_details"
        }},
        {"$unwind": "$pet_details"},       
        {"$lookup": {
            "from": "Pet_Condition",        
            "localField": "pet_details.pet_condition_id",  
            "foreignField": "pet_condition_id",            
            "as": "condition_info"
        }},
        {"$unwind": {
            "path": "$condition_info",
            "preserveNullAndEmptyArrays": True
        }},
        {"$addFields": {"pet_details.condition_info": "$condition_info"}},  
        {"$replaceRoot": {"newRoot": "$pet_details"}}  
    ]

    try:
        favourited_pets = await db["Favourites"].aggregate(pipeline).to_list(length=None)

        for pet in favourited_pets:
            if "_id" in pet:
                pet["_id"] = str(pet["_id"])
            if pet.get('condition_info') and '_id' in pet['condition_info']:
                pet['condition_info']['_id'] = str(pet['condition_info']['_id'])

        return jsonify(favourited_pets), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# WORKING
@app.route('/api/v1/addtocart', methods=['POST'])
async def add_to_cart():
    data = request.json
    user_id = data.get('user_id')
    pet_id = data.get('pet_id')

    if not user_id:
        return jsonify({"error": "User not logged in"}), 401 

    db = await get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    cart_collection = db['Cart']
    
    try:
        existing_cart_item = await cart_collection.find_one({"user_id": user_id, "pet_id": pet_id})
        if existing_cart_item:
            return jsonify({"error": "Pet is already in cart"}), 400

        last_cart_item = await cart_collection.find_one(sort=[("cart_id", -1)])
        next_cart_id = last_cart_item['cart_id'] + 1 if last_cart_item else 1

        await cart_collection.insert_one({
            "cart_id": next_cart_id,
            "user_id": user_id,
            "pet_id": pet_id
        })

        return jsonify({"message": "Pet added to cart successfully", "cart_id": next_cart_id, "pet_id": pet_id}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# WORKING
@app.route('/api/v1/getcart', methods=['POST'])
async def get_cart():
    data = request.json
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    db = await get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    pipeline = [
        {"$match": {"user_id": user_id}}, 
        {"$lookup": {
            "from": "Pets_Info",
            "localField": "pet_id",
            "foreignField": "pet_id",
            "as": "pets_info"
        }},
        {"$unwind": "$pets_info"},  
        {"$lookup": {
            "from": "Pet_Condition",
            "localField": "pets_info.pet_condition_id",
            "foreignField": "pet_condition_id",
            "as": "pets_info.pet_condition"
        }},
        {"$unwind": "$pets_info.pet_condition"}, 
        {"$lookup": {
            "from": "Condition_Info",
            "localField": "pets_info.pet_condition.condition_info_id",
            "foreignField": "condition_info_id",
            "as": "pets_info.pet_condition.condition_info"
        }},
        {"$unwind": {
            "path": "$pets_info.pet_condition.condition_info",
            "preserveNullAndEmptyArrays": True
        }},  
        {"$project": {
            "cart_id": 1,
            "user_id": 1,
            "pet_id": "$pets_info.pet_id",
            "name": "$pets_info.name",
            "type": "$pets_info.type",
            "breed": "$pets_info.breed",
            "gender": "$pets_info.gender",
            "age_month": "$pets_info.age_month",
            "description": "$pets_info.description",
            "adoption_status": "$pets_info.adoption_status",
            "image": "$pets_info.image",  
            "pet_condition": "$pets_info.pet_condition"  
        }}
    ]

    try:
        cart = await db["Cart"].aggregate(pipeline).to_list(length=None)

        for item in cart:
            if '_id' in item:
                item['_id'] = str(item['_id'])
            if 'pet_condition' in item and '_id' in item['pet_condition']:
                item['pet_condition']['_id'] = str(item['pet_condition']['_id'])

        return jsonify(cart), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# Working
@app.route('/api/v1/removefromcart', methods=['POST'])
async def remove_from_cart():
    data = request.json
    user_id = data.get('user_id')
    pet_id = data.get('pet_id')

    if not user_id or not pet_id:
        return jsonify({"error": "Missing user_id or pet_id"}), 400

    db = await get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    cart_collection = db['Cart']

    try:
        result = await cart_collection.delete_one({"user_id": user_id, "pet_id": pet_id})

        if result.deleted_count == 0:
            return jsonify({"error": "Item not found in cart"}), 404

        return jsonify("Success"), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# conversion to transactions
@app.route('/api/v1/confirmReservation', methods=['POST'])
async def confirm_reservation():
    data = request.json
    user_id = data.get('user_id')
    cart = data.get('cart')

    if not user_id or not cart:
        return jsonify({"error": "Missing user_id or cart"}), 400
    
    db = await get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    # get collection references
    applications_collection = db['Applications']
    cart_collection = db['Cart']
    pets_info_collection = db['Pets_Info']

    async with await db.client.start_session() as session:
        try:
            # starting the transaction
            async with session.start_transaction():
                # process each pet in the cart within the transaction
                for item in cart:
                    pet_id = item.get('pet_id')
                    submission_date = datetime.now(timezone.utc)
                    status = 'pending'

                    pet_info = await pets_info_collection.find_one(
                        {"pet_id": pet_id, "adoption_status": "Available"},
                        session=session
                    )
                    if not pet_info:
                        raise ValueError(f"Pet {pet_id} is not available for adoption")

                    # find max application_id within the transaction
                    last_application = await applications_collection.find_one(
                        sort=[("application_id", -1)],
                        session=session
                    )
                    next_application_id = last_application['application_id'] + 1 if last_application else 1

                    # insert the new application within the transaction
                    await applications_collection.insert_one({
                        "application_id": next_application_id,
                        "user_id": user_id,
                        "pet_id": pet_id,
                        "submission_date": submission_date,
                        "status": status
                    }, session=session)

                    # update pet's adoption status to pending
                    await pets_info_collection.update_one(
                        {"pet_id": pet_id},
                        {"$set": {"adoption_status": "Pending"}},
                        session=session
                    )

                # remove all items from the cart within the transaction
                await cart_collection.delete_many({"user_id": user_id}, session=session)

                return jsonify({"message": "Reservation confirmed successfully"}), 200

        except ValueError as e:
            # handle validation errors
            return jsonify({"error": str(e)}), 400
        except DuplicateKeyError:
            # handle duplicate application errors
            return jsonify({"error": "Application already exists"}), 400
        except Exception as e:
            # rollback the transaction in case of an error
            return jsonify({"error": f"Transaction failed: {str(e)}"}), 500

"""
--- Admin Endpoints ---
"""

# WORKING
@app.route('/api/v1/admin/deletePet', methods=['POST'])
async def admin_delete_pet():
    data = request.json
    pet_id = data.get('pet_id')
    user_id = data.get('user_id')

    db = await get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    # get collection references
    users_collection = db['Users']
    pet_info_collection = db['Pets_Info']
    pet_condition_collection = db['Pet_Condition']
    favourites_collection = db['Favourites']
    cart_collection = db['Cart']
    applications_collection = db['Applications']

    # start session for transaction
    async with await db.client.start_session() as session:
        try:
            # starting the transaction
            async with session.start_transaction():
                # check if the user has admin permissions
                user = await users_collection.find_one(
                    {"user_id": user_id}, 
                    session=session
                )
                if not user or user.get("role") != "admin":
                    raise ValueError("Invalid Permissions")

                # get the pet_condition_id from Pet_Info
                pet_info = await pet_info_collection.find_one(
                    {"pet_id": pet_id}, 
                    session=session
                )
                if pet_info is None:
                    raise ValueError("Pet not found")

                pet_condition_id = pet_info.get("pet_condition_id")

                # delete associated records in Favourites, Cart, and Applications within transaction
                await favourites_collection.delete_many(
                    {"pet_id": pet_id}, 
                    session=session
                )
                await cart_collection.delete_many(
                    {"pet_id": pet_id}, 
                    session=session
                )
                await applications_collection.delete_many(
                    {"pet_id": pet_id}, 
                    session=session
                )

                # delete the pet from Pet_Info within transaction
                await pet_info_collection.delete_one(
                    {"pet_id": pet_id}, 
                    session=session
                )

                # delete the pet condition from Pet_Condition within transaction
                await pet_condition_collection.delete_one(
                    {"pet_condition_id": pet_condition_id}, 
                    session=session
                )

                return jsonify({"message": "Pet deleted successfully"}), 200

        except ValueError as e:
            # handle validation errors
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            # rollback the transaction in case of an error
            return jsonify({"error": f"Transaction failed: {str(e)}"}), 500

# working
@app.route('/api/v1/admin/editPet', methods=['POST'])
async def admin_edit_pet():
    data = request.json
    pet_data = data.get('pet_data')
    user_id = data.get('user_id')
    pet_id = pet_data.get('pet_id')

    if not pet_data or not user_id:
        return jsonify({"error": "Missing required fields"}), 400

    db = await get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    users_collection = db['Users']
    pet_info_collection = db['Pets_Info']
    pet_condition_collection = db['Pet_Condition']

    try:
        user = await users_collection.find_one({"user_id": user_id})
        if not user or user.get("role") != "admin":
            return jsonify({"error": "Invalid Permissions"}), 400

        pet_info = await pet_info_collection.find_one({"pet_id": pet_id})
        if pet_info is None:
            return jsonify({"error": "Pet not found"}), 404

        pet_condition_id = pet_info.get("pet_condition_id")
        if not pet_condition_id:
            return jsonify({"error": "Pet condition not linked"}), 404

        vaccination_date_str = pet_data.get('vaccination_date')
        formatted_vaccination_date = None
        if vaccination_date_str:
            try:
                formatted_vaccination_date = datetime.strptime(vaccination_date_str, '%a, %d %b %Y %H:%M:%S %Z')
            except ValueError as e:
                print(f"Error parsing vaccination date: {e}")

        pet_type = pet_data.get('type')
        new_type = ','.join(pet_type) if isinstance(pet_type, list) else pet_type
        gender = pet_data.get('gender')
        new_gender = gender[0] if isinstance(gender, list) and gender else gender

        pet_info_update = {
            "name": pet_data.get('name'),
            "type": new_type,
            "breed": pet_data.get('breed'),
            "gender": new_gender,
            "age_month": int(pet_data.get('age_month')),
            "description": pet_data.get('description')
        }
        await pet_info_collection.update_one(
            {"pet_id": pet_id},
            {"$set": pet_info_update}
        )

        condition_update_data = {
            "weight": int(pet_data.get('weight')) if pet_data.get('weight') else 0,
            "health_condition": pet_data.get('health_condition'),
            "sterilisation_status": int(pet_data.get('sterilisation_status')) if pet_data.get('sterilisation_status') else 0,
            "adoption_fee": int(pet_data.get('adoption_fee')) if pet_data.get('adoption_fee') else 0,
            "previous_owner": int(pet_data.get('previous_owner')) if pet_data.get('previous_owner') else 0
        }

        if formatted_vaccination_date:
            condition_update_data["vaccination_date"] = formatted_vaccination_date

        await pet_condition_collection.update_one(
            {"pet_condition_id": pet_condition_id},
            {"$set": condition_update_data}
        )

        return jsonify({"message": "Pet updated successfully"}), 200

    except Exception as e:
        print(f"Error in admin_edit_pet: {str(e)}")
        return jsonify({"error": str(e)}), 500

# WORKING
@app.route('/api/v1/admin/addPet', methods=['POST'])
async def admin_add_pet():
    data = request.json
    pet_data = data.get('pet_data')
    user_id = data.get('user_id')

    if not pet_data or not user_id:
        return jsonify({"error": "Missing required fields"}), 400

    db = await get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    users_collection = db['Users']
    pet_condition_collection = db['Pet_Condition']
    pet_info_collection = db['Pets_Info']

    async with await db.client.start_session() as session:
        try:
            # starting the transaction
            async with session.start_transaction():
                # verify admin permissions within transaction
                user = await users_collection.find_one(
                    {"user_id": user_id},
                    session=session
                )
                if not user or user.get("role") != "admin":
                    raise ValueError("Invalid Permissions")

                # get next pet_id within transaction
                last_pet = await pet_info_collection.find_one(
                    sort=[("pet_id", -1)],
                    session=session
                )
                next_pet_id = (last_pet['pet_id'] + 1) if last_pet else 1

                # get next condition_id within transaction
                last_condition = await pet_condition_collection.find_one(
                    sort=[("pet_condition_id", -1)],
                    session=session
                )
                next_pet_condition_id = (last_condition['pet_condition_id'] + 1) if last_condition else 1

                # parse vaccination date
                vaccination_date_str = pet_data.get('vaccination_date')
                formatted_vaccination_date = None
                if vaccination_date_str:
                    try:
                        formatted_vaccination_date = datetime.fromisoformat(
                            vaccination_date_str.replace("Z", "+00:00")
                        )
                    except ValueError:
                        raise ValueError("Invalid vaccination date format")

                # create pet condition within transaction
                pet_condition_data = {
                    "pet_condition_id": next_pet_condition_id,
                    "weight": int(pet_data.get('weight')),
                    "vaccination_date": formatted_vaccination_date,
                    "health_condition": pet_data.get('health_condition'),
                    "sterilisation_status": int(pet_data.get('sterilisation_status')),
                    "adoption_fee": int(pet_data.get('adoption_fee')),
                    "previous_owner": int(pet_data.get('previous_owner'))
                }
                await pet_condition_collection.insert_one(
                    pet_condition_data,
                    session=session
                )

                # create pet info within transaction
                pet_info_data = {
                    "pet_id": next_pet_id,
                    "name": pet_data.get('name'),
                    "type": pet_data.get('type'),
                    "breed": pet_data.get('breed'),
                    "gender": pet_data.get('gender'),
                    "age_month": int(pet_data.get('age_month')),
                    "description": pet_data.get('description'),
                    "image": pet_data.get('image'),
                    "adoption_status": "Available",
                    "pet_condition_id": next_pet_condition_id
                }
                await pet_info_collection.insert_one(
                    pet_info_data,
                    session=session
                )

                return jsonify({
                    "message": "Pet added successfully", 
                    "pet_id": next_pet_id
                }), 200

        except ValueError as e:
            # handle validation errors
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            # rollback the transaction in case of an error
            return jsonify({"error": f"Transaction failed: {str(e)}"}), 500

@app.route('/api/v1/admin/getUsers', methods=['POST'])
async def admin_get_users():
    data = request.json
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    db = await get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        users_collection = db['Users']
        user = await users_collection.find_one({"user_id": user_id})

        if not user or user.get("role") != "admin":
            return jsonify({"error": "Invalid Permissions"}), 403

        users = await users_collection.find({}, {"user_id": 1, "username": 1, "role": 1, "_id": 0}).to_list(length=None)

        return jsonify({
            "status": "success",
            "users": users
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/v1/admin/deleteUser/<int:user_id>', methods=['POST'])
async def admin_delete_user(user_id):
    data = request.json
    admin_id = data.get('admin_id')

    db = await get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        users_collection = db['Users']

        admin_user = await users_collection.find_one({"user_id": admin_id})
        if not admin_user or admin_user.get("role") != "admin":
            return jsonify({"error": "Invalid Permissions"}), 403

        result = await users_collection.delete_one({"user_id": user_id})

        if result.deleted_count == 0:
            return jsonify({"error": "User not found"}), 404

        return jsonify({"message": "User deleted successfully"}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

from werkzeug.security import generate_password_hash

@app.route('/api/v1/admin/addUser', methods=['POST'])
async def admin_add_user():
    data = request.json
    admin_id = data.get('admin_id')
    username = data.get('username')
    password = data.get('password')
    role = data.get('role')

    if not all([admin_id, username, password, role]):
        return jsonify({"error": "All fields are required"}), 400

    db = await get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        users_collection = db['Users']

        admin_user = await users_collection.find_one({"user_id": admin_id})
        if not admin_user or admin_user.get("role") != "admin":
            return jsonify({"error": "Invalid Permissions"}), 403

        hashed_password = generate_password_hash(password)

        last_user = await users_collection.find_one(sort=[("user_id", -1)])
        next_user_id = last_user['user_id'] + 1 if last_user else 1

        new_user = {
            "user_id": next_user_id,
            "username": username,
            "password": hashed_password,
            "role": role
        }
        await users_collection.insert_one(new_user)

        return jsonify({"status": "success", "message": "User added successfully"}), 201

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/v1/admin/getUser/<int:user_id>', methods=['POST'])
async def admin_get_user(user_id):
    data = request.json
    admin_id = data.get('admin_id')

    if not admin_id:
        return jsonify({"error": "Admin ID is required"}), 400

    db = await get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        users_collection = db['Users']

        admin_user = await users_collection.find_one({"user_id": admin_id})
        if not admin_user or admin_user.get("role") != "admin":
            return jsonify({"error": "Invalid Permissions"}), 403
        
        user = await users_collection.find_one({"user_id": user_id}, {"_id": 0, "user_id": 1, "username": 1, "role": 1})

        if not user:
            return jsonify({"error": "User not found"}), 404

        return jsonify({
            "status": "success",
            "user": user
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# WORKING
@app.route('/api/v1/admin/updateUser/<int:user_id>', methods=['POST'])
async def admin_update_user(user_id):
    data = request.json
    admin_id = data.get('admin_id')
    username = data.get('username')
    role = data.get('role')

    if not all([admin_id, username, role]):
        return jsonify({"error": "All fields are required"}), 400

    db = await get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        users_collection = db['Users']
        admin_user = await users_collection.find_one({"user_id": admin_id})
        if not admin_user or admin_user.get("role") != "admin":
            return jsonify({"error": "Invalid Permissions"}), 403

        user = await users_collection.find_one({"user_id": user_id})
        if not user:
            return jsonify({"error": "User not found"}), 404

        current_role = user.get("role")
        if current_role == "adopter" and role == "admin":
            print(f"Escalating privileges for user_id {user_id} from 'adopter' to 'admin'.")


        result = await users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"username": username, "role": role}}
        )

        if result.matched_count == 0:
            return jsonify({"error": "User not found or no changes made"}), 404

        return jsonify({
            "status": "success",
            "message": f"User updated successfully to role: {role}"
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

from bson import ObjectId

@app.route('/api/v1/admin/getApplications', methods=['POST'])
async def admin_get_applications():
    data = request.json
    admin_id = data.get('admin_id')

    if not admin_id:
        return jsonify({"error": "Admin ID is required"}), 400

    db = await get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        users_collection = db['Users']
        applications_collection = db['Applications']
        pets_info_collection = db['Pets_Info']

        admin_user = await users_collection.find_one({"user_id": admin_id})
        if not admin_user or admin_user.get("role") != "admin":
            return jsonify({"error": "Invalid Permissions"}), 403

        applications = await applications_collection.aggregate([
            {
                "$lookup": {
                    "from": "Users",
                    "localField": "user_id",
                    "foreignField": "user_id",
                    "as": "user_info"
                }
            },
            {
                "$lookup": {
                    "from": "Pets_Info",
                    "localField": "pet_id",
                    "foreignField": "pet_id",
                    "as": "pet_info"
                }
            },
            {"$unwind": "$user_info"},
            {"$unwind": "$pet_info"},
            {
                "$project": {
                    "application_id": 1,
                    "user_id": 1,
                    "pet_id": 1,
                    "submission_date": 1,
                    "status": 1,
                    "username": "$user_info.username",
                    "pet_name": "$pet_info.name"
                }
            }
        ]).to_list(length=None)

        for application in applications:
            application['_id'] = str(application['_id'])

        return jsonify({
            "status": "success",
            "applications": applications
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/v1/admin/getApplications/<int:application_id>', methods=['POST'])
async def admin_get_application_detail(application_id):
    data = request.json
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    db = await get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        users_collection = db['Users']
        applications_collection = db['Applications']
        pets_info_collection = db['Pets_Info']

        admin_user = await users_collection.find_one({"user_id": user_id})
        if not admin_user or admin_user.get("role") != "admin":
            return jsonify({"error": "Invalid Permissions"}), 403

        application_detail = await applications_collection.aggregate([
            {"$match": {"application_id": application_id}}, 
            {"$lookup": {
                "from": "Users",
                "localField": "user_id",
                "foreignField": "user_id",
                "as": "user_info"
            }},
            {"$lookup": {
                "from": "Pets_Info",
                "localField": "pet_id",
                "foreignField": "pet_id",
                "as": "pet_info"
            }},
            {"$unwind": "$user_info"},
            {"$unwind": "$pet_info"},
            {"$project": {
                "application_id": 1,
                "submission_date": 1,
                "status": 1,
                "pet_id": "$pet_info.pet_id",
                "pet_name": "$pet_info.name",
                "pet_type": "$pet_info.type",
                "breed": "$pet_info.breed",
                "gender": "$pet_info.gender",
                "age_month": "$pet_info.age_month",
                "pet_description": "$pet_info.description",
                "pet_image": "$pet_info.image",
                "applicant_id": "$user_info.user_id",
                "applicant_username": "$user_info.username"
            }}
        ]).to_list(length=None)

        if not application_detail:
            return jsonify({
                "status": "error",
                "message": "Application not found"
            }), 404
        
        application = application_detail[0]
        if 'submission_date' in application and isinstance(application['submission_date'], datetime):
            application['submission_date'] = application['submission_date'].isoformat()

        for key, value in application.items():
            if isinstance(value, ObjectId):
                application[key] = str(value)
        
        return jsonify({
            "status": "success",
            "application": application
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    

@app.route('/api/v1/admin/updateApplicationStatus/<int:application_id>', methods=['POST'])
async def update_application_status(application_id):
    data = request.json
    new_status = data.get('status')
    admin_id = data.get('user_id')  
    applicant_id = data.get('applicant_id')  
    pet_id = data.get('pet_id')

    db = await get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    # get collection references
    users_collection = db['Users']
    applications_collection = db['Applications']
    adoptions_collection = db['Adoptions']
    pets_info_collection = db['Pets_Info']

    async with await db.client.start_session() as session:
        try:
            # starting the transaction
            async with session.start_transaction():
                # verify admin permissions within transaction
                admin_user = await users_collection.find_one(
                    {"user_id": admin_id},
                    session=session
                )
                if not admin_user or admin_user.get("role") != "admin":
                    raise ValueError("Invalid Permissions")

                # update application status within transaction
                update_result = await applications_collection.update_one(
                    {"application_id": application_id},
                    {"$set": {"status": new_status}},
                    session=session
                )

                if update_result.matched_count == 0:
                    raise ValueError("Application not found")

                # if approved, handle adoption process
                if new_status == 'approved':
                    # update pet status within transaction
                    pet_result = await pets_info_collection.update_one(
                        {"pet_id": pet_id},
                        {"$set": {"adoption_status": "Unavailable"}},
                        session=session
                    )

                    if pet_result.modified_count == 0:
                        raise ValueError("Failed to update pet status")

                    # get next adoption id within transaction
                    last_adoption = await adoptions_collection.find_one(
                        sort=[("adoption_id", -1)],
                        session=session
                    )
                    next_adoption_id = last_adoption["adoption_id"] + 1 if last_adoption else 1

                    # create adoption record within transaction
                    adoption_data = {
                        "adoption_id": next_adoption_id,
                        "application_id": application_id,
                        "adoption_date": datetime.now(timezone.utc),
                        "pet_id": pet_id,
                        "user_id": applicant_id
                    }
                    await adoptions_collection.insert_one(adoption_data, session=session)

                return jsonify({
                    "status": "success",
                    "message": "Application status updated successfully"
                })

        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            # rollback the transaction in case of an error
            return jsonify({"error": f"Transaction failed: {str(e)}"}), 500


@app.route('/api/v1/admin/getAdoptions', methods=['POST'])
async def admin_get_adoptions():
    data = request.json
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    db = await get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        users_collection = db['Users']
        adoptions_collection = db['Adoptions']
        pets_info_collection = db['Pets_Info']
        applications_collection = db['Applications']

        admin_user = await users_collection.find_one({"user_id": user_id})
        if not admin_user or admin_user.get("role") != "admin":
            return jsonify({"error": "Invalid Permissions"}), 403

        adoptions = await adoptions_collection.aggregate([
            {
                "$lookup": {
                    "from": "Users",
                    "localField": "user_id",
                    "foreignField": "user_id",
                    "as": "adopter_info"
                }
            },
            {"$unwind": "$adopter_info"}, 
            {
                "$lookup": {
                    "from": "Pets_Info",
                    "localField": "pet_id",
                    "foreignField": "pet_id",
                    "as": "pet_info"
                }
            },
            {"$unwind": "$pet_info"}, 

            {
                "$lookup": {
                    "from": "Applications",
                    "localField": "application_id",
                    "foreignField": "application_id",
                    "as": "application_info"
                }
            },
            {"$unwind": "$application_info"}, 
            {
                "$project": {
                    "adoption_id": 1,
                    "adoption_date": 1,
                    "adopter_id": "$adopter_info.user_id",
                    "adopter_name": "$adopter_info.username",
                    "pet_id": "$pet_info.pet_id",
                    "pet_name": "$pet_info.name",
                    "pet_type": "$pet_info.type",
                    "pet_breed": "$pet_info.breed",
                    "application_id": "$application_info.application_id",
                    "application_date": "$application_info.submission_date",
                    "application_status": "$application_info.status"
                }
            },
            {"$sort": {"adoption_date": -1}}
        ]).to_list(length=None)

        for adoption in adoptions:
            for key, value in adoption.items():
                if isinstance(value, ObjectId):
                    adoption[key] = str(value)
                elif isinstance(value, datetime):
                    adoption[key] = value.isoformat()

        return jsonify({
            "status": "success",
            "adoptions": adoptions
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500



if __name__ == '__main__':
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    loop = asyncio.get_event_loop()
    db = loop.run_until_complete(get_db_connection())
    if db:
        loop.run_until_complete(create_indexes(db))

    app.run(debug=True)
