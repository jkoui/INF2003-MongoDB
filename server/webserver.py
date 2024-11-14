from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime, timezone
from pymongo.errors import DuplicateKeyError
from bson import ObjectId
import os

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}}, supports_credentials=True)
app.secret_key = "inf2002dbprojectpartone"

def get_db_connection():
    try:
        client = MongoClient(os.getenv("MONGO_URI"))
        client.admin.command('ping')
        db = client[os.getenv("DATABASE_NAME")]
        return db
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return None

@app.route('/api/v1')
def index():
    return jsonify({"message": "index"}), 200

"""
--- User Log In Endpoints ---

"""

@app.route('/api/v1/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Missing required fields"}), 400

    hashed_password = generate_password_hash(password)
    db = get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    user_collection = db['Users']
    
    try:
        # Find the current maximum user_id
        last_user = user_collection.find_one(sort=[("user_id", -1)])
        # If there is no user, start from 1; otherwise, increment from the maximum
        next_user_id = last_user['user_id'] + 1 if last_user else 1
        # Insert the new user with the next user_id
        user_collection.insert_one({
            "user_id": next_user_id,
            "username": username,
            "password": hashed_password,
            "role": "adopter"
        })
        return jsonify({"message": "User registered successfully", "user_id": next_user_id}), 201

    except DuplicateKeyError:
        return jsonify({"error": "Username already exists"}), 400
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Missing username or password"}), 400

    db = get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    user_collection = db['Users']
    user = user_collection.find_one({"username": username})

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

# WORKING
@app.route('/api/v1/getPets', methods=['GET'])
def get_all_pets():
    db = get_db_connection()

    if db is None:
        return jsonify({"error": "Database connection failed"}), 500
    pet_info_collection = db['Pets_Info']
    pipeline = [
        {
            "$lookup": {
                "from": "Pet_Condition",
                "localField": "pet_condition_id",
                "foreignField": "pet_condition_id",
                "as": "condition_info"
            }
        },
        {
            "$unwind": {
                "path": "$condition_info",
                "preserveNullAndEmptyArrays": True
            }
        }
    ]
    pets = list(pet_info_collection.aggregate(pipeline))

    for pet in pets:
        pet['_id'] = str(pet['_id'])
        if pet.get('condition_info') and '_id' in pet['condition_info']:
            pet['condition_info']['_id'] = str(pet['condition_info']['_id'])
    return jsonify(pets), 200

# WORKING
@app.route('/api/v1/getTop3', methods=['GET'])
def get_top3():
    db = get_db_connection()  

    if db is None:
        return jsonify([]), 500  

    try:
        top3_pets = list(db['Pets_Info'].aggregate([
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
        ]))

        for pet in top3_pets:
            if '_id' in pet:
                pet['_id'] = str(pet['_id'])

        return jsonify(top3_pets), 200 

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# WORKING
@app.route('/api/v1/filterpets', methods=['POST'])
def filter_pets():
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

    db = get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        pets_info_collection = db['Pets_Info']

        # Aggregation pipeline with match conditions
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
        pets = list(pets_info_collection.aggregate(pipeline))

        # Convert ObjectId fields to strings
        for pet in pets:
            for key, value in pet.items():
                if isinstance(value, ObjectId):
                    pet[key] = str(value)
            if "condition_info" in pet:
                for key, value in pet["condition_info"].items():
                    if isinstance(value, ObjectId):
                        pet["condition_info"][key] = str(value)

        return jsonify(pets), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# WORKING
@app.route('/api/v1/addFavourite', methods=['POST'])
def add_favourite():
    data = request.json
    pet_id = data.get('pet_id')
    user_id = data.get('user_id')

    if not pet_id:
        return jsonify({"error": "Pet ID is required"}), 400
    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    print(f"Received user_id: {user_id} of type {type(user_id)}")

    # Ensure that user_id is an integer
    try:
        user_id = int(user_id)  # Convert to integer if it's not already
    except ValueError:
        return jsonify({"error": "User ID must be an integer"}), 400

    db = get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    favourites_collection = db['Favourites']
    
    try:
        # Check if the pet is already in the user's favourites
        existing_favourite = favourites_collection.find_one({"user_id": user_id, "pet_id": pet_id})
        if existing_favourite:
            return jsonify({"error": "Pet is already in favourites"}), 400

        # Find the current maximum favourite_id
        last_favourite = favourites_collection.find_one(sort=[("favourite_id", -1)])
        # If there are no favourites, start from 1; otherwise, increment from the maximum
        next_favourite_id = last_favourite['favourite_id'] + 1 if last_favourite else 1

        # Insert the new favourite document with integer user_id
        favourites_collection.insert_one({
            "favourite_id": next_favourite_id,
            "user_id": user_id,  # This will be stored as an integer
            "pet_id": pet_id
        })

        return jsonify({"message": "Pet added to favourites successfully"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


    
@app.route('/api/v1/getReservedPets', methods=['GET'])
def get_reserved_pets():
    db = get_db_connection()
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

    pets_in_applications = list(db["Pets_Info"].aggregate(pipeline))

    # Convert ObjectIds to strings for JSON compatibility
    for pet in pets_in_applications:
        pet['_id'] = str(pet['_id'])

    return jsonify(pets_in_applications), 200


# WORKING
@app.route('/api/v1/getFavourites', methods=['GET'])
def get_favourites():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    # Convert user_id to integer if it's stored as an integer in MongoDB
    try:
        user_id = int(user_id)
    except ValueError:
        return jsonify({"error": "Invalid user_id format"}), 400

    db = get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    # Aggregation pipeline to match favourites and join with pet info and condition
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$lookup": {
            "from": "Pets_Info",            # Collection to join with
            "localField": "pet_id",         # Field in Favourites collection
            "foreignField": "pet_id",       # Field in Pet_Info collection
            "as": "pet_details"
        }},
        {"$unwind": "$pet_details"},       # Unwind to get pet details as a flat structure
        {"$lookup": {
            "from": "Pet_Condition",        # Collection to join with for pet condition info
            "localField": "pet_details.pet_condition_id",  # Field in pet details
            "foreignField": "pet_condition_id",            # Field in Pet_Condition collection
            "as": "condition_info"
        }},
        {"$unwind": {
            "path": "$condition_info",
            "preserveNullAndEmptyArrays": True
        }},
        {"$addFields": {"pet_details.condition_info": "$condition_info"}},  # Embed condition info in pet details
        {"$replaceRoot": {"newRoot": "$pet_details"}}  # Replace root with pet details including condition info
    ]

    try:
        # Run the aggregation pipeline
        favourited_pets = list(db["Favourites"].aggregate(pipeline))

        # Convert ObjectIds to strings for JSON compatibility
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
def add_to_cart():
    data = request.json
    user_id = data.get('user_id')
    pet_id = data.get('pet_id')

    if not user_id:
        return jsonify({"error": "User not logged in"}), 401 

    db = get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    cart_collection = db['Cart']
    
    try:
        # Check if the pet is already in the user's cart
        existing_cart_item = cart_collection.find_one({"user_id": user_id, "pet_id": pet_id})
        if existing_cart_item:
            return jsonify({"error": "Pet is already in cart"}), 400

        # Find the current maximum cart_id
        last_cart_item = cart_collection.find_one(sort=[("cart_id", -1)])
        # If there are no items in the cart, start from 1; otherwise, increment from the maximum
        next_cart_id = last_cart_item['cart_id'] + 1 if last_cart_item else 1

        # Insert the new cart item with cart_id
        cart_collection.insert_one({
            "cart_id": next_cart_id,
            "user_id": user_id,
            "pet_id": pet_id
        })

        return jsonify({"message": "Pet added to cart successfully", "cart_id": next_cart_id, "pet_id": pet_id}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# WORKING
@app.route('/api/v1/getcart', methods=['POST'])
def get_cart():
    data = request.json
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    db = get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    # Define the aggregation pipeline
    pipeline = [
        {"$match": {"user_id": user_id}},  # Filter by user_id in the Cart collection
        {"$lookup": {
            "from": "Pets_Info",
            "localField": "pet_id",
            "foreignField": "pet_id",
            "as": "pets_info"
        }},
        {"$unwind": "$pets_info"},  # Flatten pet_info array to include each pet's details
        {"$lookup": {
            "from": "Pet_Condition",
            "localField": "pets_info.pet_condition_id",
            "foreignField": "pet_condition_id",
            "as": "pets_info.pet_condition"
        }},
        {"$unwind": "$pets_info.pet_condition"},  # Flatten pet_condition array
        {"$lookup": {
            "from": "Condition_Info",
            "localField": "pets_info.pet_condition.condition_info_id",
            "foreignField": "condition_info_id",
            "as": "pets_info.pet_condition.condition_info"
        }},
        {"$unwind": {
            "path": "$pets_info.pet_condition.condition_info",
            "preserveNullAndEmptyArrays": True
        }},  # Flatten pet_condition array
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
            "pet_condition": "$pets_info.pet_condition"  # Include pet condition details
        }}
    ]

    try:
        # Run the aggregation pipeline
        cart = list(db["Cart"].aggregate(pipeline))

        # Convert ObjectIds to strings for JSON compatibility
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
def remove_from_cart():
    data = request.json
    user_id = data.get('user_id')
    pet_id = data.get('pet_id')

    if not user_id or not pet_id:
        return jsonify({"error": "Missing user_id or pet_id"}), 400

    db = get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    cart_collection = db['Cart']

    try:
        # Remove the item from the cart where user_id and pet_id match
        result = cart_collection.delete_one({"user_id": user_id, "pet_id": pet_id})

        if result.deleted_count == 0:
            # No document was deleted, which means the item wasn't found
            return jsonify({"error": "Item not found in cart"}), 404

        return jsonify("Success"), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# WORKING
@app.route('/api/v1/confirmReservation', methods=['POST'])
def confirm_reservation():
    data = request.json
    user_id = data.get('user_id')
    cart = data.get('cart')

    if not user_id or not cart:
        return jsonify({"error": "Missing user_id or cart"}), 400

    db = get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    applications_collection = db['Applications']
    cart_collection = db['Cart']

    try:
        # For each pet in the cart, create a new application
        for item in cart:
            pet_id = item.get('pet_id')
            submission_date = datetime.now(timezone.utc)
            status = 'pending'

            # Find the current maximum application_id and increment it
            last_application = applications_collection.find_one(sort=[("application_id", -1)])
            next_application_id = last_application['application_id'] + 1 if last_application else 1

            # Insert the new application
            applications_collection.insert_one({
                "application_id": next_application_id,
                "user_id": user_id,
                "pet_id": pet_id,
                "submission_date": submission_date,
                "status": status
            })

        # Remove all items from the Cart collection for this user
        cart_collection.delete_many({"user_id": user_id})

        return jsonify("Success"), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
"""
--- Admin Endpoints ---
"""

# WORKING
@app.route('/api/v1/admin/deletePet', methods=['POST'])
def admin_login():
    data = request.json
    pet_id = data.get('pet_id')
    user_id = data.get('user_id')

    db = get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    users_collection = db['Users']
    pet_info_collection = db['Pets_Info']
    pet_condition_collection = db['Pet_Condition']
    favourites_collection = db['Favourites']
    cart_collection = db['Cart']
    applications_collection = db['Applications']

    try:
        # Check if the user has admin permissions
        user = users_collection.find_one({"user_id": user_id})
        if not user or user.get("role") != "admin":
            return jsonify({"error": "Invalid Permissions"}), 400

        # Get the pet_condition_id from Pet_Info
        pet_info = pet_info_collection.find_one({"pet_id": pet_id})
        if pet_info is None:
            return jsonify({"error": "Pet not found"}), 404

        pet_condition_id = pet_info.get("pet_condition_id")

        # Delete associated records in Favourites, Cart, and Applications
        favourites_collection.delete_many({"pet_id": pet_id})
        cart_collection.delete_many({"pet_id": pet_id})
        applications_collection.delete_many({"pet_id": pet_id})

        # Delete the pet from Pet_Info
        pet_info_collection.delete_one({"pet_id": pet_id})

        # Delete the pet condition from Pet_Condition
        pet_condition_collection.delete_one({"pet_condition_id": pet_condition_id})

        return jsonify({"message": "Pet deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# working
@app.route('/api/v1/admin/editPet', methods=['POST'])
def admin_edit_pet():
    data = request.json
    pet_data = data.get('pet_data')
    user_id = data.get('user_id')
    pet_id = pet_data.get('pet_id')

    if not pet_data or not user_id:
        return jsonify({"error": "Missing required fields"}), 400

    db = get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    users_collection = db['Users']
    pet_info_collection = db['Pets_Info']
    pet_condition_collection = db['Pet_Condition']

    try:
        # Check if the user has admin permissions
        user = users_collection.find_one({"user_id": user_id})
        if not user or user.get("role") != "admin":
            return jsonify({"error": "Invalid Permissions"}), 400

        # Get the pet_condition_id from Pet_Info
        pet_info = pet_info_collection.find_one({"pet_id": pet_id})
        if pet_info is None:
            return jsonify({"error": "Pet not found"}), 404

        pet_condition_id = pet_info.get("pet_condition_id")
        if not pet_condition_id:
            return jsonify({"error": "Pet condition not linked"}), 404

        # Parse vaccination_date if present
        vaccination_date_str = pet_data.get('vaccination_date')
        formatted_vaccination_date = None
        if vaccination_date_str:
            try:
                formatted_vaccination_date = datetime.strptime(vaccination_date_str, '%a, %d %b %Y %H:%M:%S %Z')
            except ValueError as e:
                print(f"Error parsing vaccination date: {e}")

        # Prepare data for Pet_Info update
        pet_type = pet_data.get('type')
        new_type = ','.join(pet_type) if isinstance(pet_type, list) else pet_type
        gender = pet_data.get('gender')
        new_gender = gender[0] if isinstance(gender, list) and gender else gender

        # Update Pet_Info collection
        pet_info_update = {
            "name": pet_data.get('name'),
            "type": new_type,
            "breed": pet_data.get('breed'),
            "gender": new_gender,
            "age_month": int(pet_data.get('age_month')),
            "description": pet_data.get('description')
        }
        pet_info_collection.update_one(
            {"pet_id": pet_id},
            {"$set": pet_info_update}
        )

        # Prepare data for Pet_Condition update
        condition_update_data = {
            "weight": int(pet_data.get('weight')) if pet_data.get('weight') else 0,
            "health_condition": pet_data.get('health_condition'),
            "sterilisation_status": int(pet_data.get('sterilisation_status')) if pet_data.get('sterilisation_status') else 0,
            "adoption_fee": int(pet_data.get('adoption_fee')) if pet_data.get('adoption_fee') else 0,
            "previous_owner": int(pet_data.get('previous_owner')) if pet_data.get('previous_owner') else 0
        }

        # Add vaccination_date to update if it was parsed successfully
        if formatted_vaccination_date:
            condition_update_data["vaccination_date"] = formatted_vaccination_date

        # Update Pet_Condition collection
        pet_condition_collection.update_one(
            {"pet_condition_id": pet_condition_id},
            {"$set": condition_update_data}
        )

        return jsonify({"message": "Pet updated successfully"}), 200

    except Exception as e:
        print(f"Error in admin_edit_pet: {str(e)}")
        return jsonify({"error": str(e)}), 500

# WORKING
@app.route('/api/v1/admin/addPet', methods=['POST'])
def admin_add_pet():
    data = request.json
    pet_data = data.get('pet_data')
    user_id = data.get('user_id')

    if not pet_data or not user_id:
        return jsonify({"error": "Missing required fields"}), 400

    db = get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        users_collection = db['Users']
        pet_condition_collection = db['Pet_Condition']
        pet_info_collection = db['Pets_Info']

        # Check if the user has admin permissions
        user = users_collection.find_one({"user_id": user_id})
        if not user or user.get("role") != "admin":
            return jsonify({"error": "Invalid Permissions"}), 400

        # Find the maximum pet_id in Pets_Info and increment by 1
        last_pet = pet_info_collection.find_one(sort=[("pet_id", -1)])
        next_pet_id = (last_pet['pet_id'] + 1) if last_pet else 1

        # Find the maximum pet_condition_id in Pet_Condition and increment by 1
        last_condition = pet_condition_collection.find_one(sort=[("pet_condition_id", -1)])
        next_pet_condition_id = (last_condition['pet_condition_id'] + 1) if last_condition else 1

        # Parse the vaccination_date in the expected format
        vaccination_date_str = pet_data.get('vaccination_date')
        formatted_vaccination_date = None
        if vaccination_date_str:
            try:
                formatted_vaccination_date = datetime.fromisoformat(vaccination_date_str.replace("Z", "+00:00"))
            except ValueError as e:
                print(f"Error parsing vaccination date: {e}")
                return jsonify({"error": "Invalid vaccination date format."}), 400

        # Insert data into Pet_Condition collection with the incremented pet_condition_id
        pet_condition_data = {
            "pet_condition_id": next_pet_condition_id,
            "weight": int(pet_data.get('weight')),
            "vaccination_date": formatted_vaccination_date,
            "health_condition": pet_data.get('health_condition'),
            "sterilisation_status": int(pet_data.get('sterilisation_status')),
            "adoption_fee": int(pet_data.get('adoption_fee')),
            "previous_owner": int(pet_data.get('previous_owner'))
        }
        pet_condition_result = pet_condition_collection.insert_one(pet_condition_data)

        # Insert data into Pet_Info collection with the incremented pet_id
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
        pet_info_collection.insert_one(pet_info_data)

        return jsonify({"message": "Pet added successfully", "pet_id": next_pet_id}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/admin/getUsers', methods=['POST'])
def admin_get_users():
    data = request.json
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    db = get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        users_collection = db['Users']

        # Check if the user has admin permissions
        user = users_collection.find_one({"user_id": user_id})
        if not user or user.get("role") != "admin":
            return jsonify({"error": "Invalid Permissions"}), 403

        # Query all users and return specific fields
        users = list(users_collection.find({}, {"user_id": 1, "username": 1, "role": 1, "_id": 0}))

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
def admin_delete_user(user_id):
    data = request.json
    admin_id = data.get('admin_id')

    db = get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        users_collection = db['Users']

        # Check if the requesting user has admin permissions
        admin_user = users_collection.find_one({"user_id": admin_id})
        if not admin_user or admin_user.get("role") != "admin":
            return jsonify({"error": "Invalid Permissions"}), 403

        # Delete the user
        result = users_collection.delete_one({"user_id": user_id})

        if result.deleted_count == 0:
            return jsonify({"error": "User not found"}), 404

        return jsonify({"message": "User deleted successfully"}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

from werkzeug.security import generate_password_hash

@app.route('/api/v1/admin/addUser', methods=['POST'])
def admin_add_user():
    data = request.json
    admin_id = data.get('admin_id')
    username = data.get('username')
    password = data.get('password')
    role = data.get('role')

    if not all([admin_id, username, password, role]):
        return jsonify({"error": "All fields are required"}), 400

    db = get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        users_collection = db['Users']

        # Check if the requesting user has admin permissions
        admin_user = users_collection.find_one({"user_id": admin_id})
        if not admin_user or admin_user.get("role") != "admin":
            return jsonify({"error": "Invalid Permissions"}), 403

        # Generate a hashed password
        hashed_password = generate_password_hash(password)

        # Find the current maximum user_id and increment it
        last_user = users_collection.find_one(sort=[("user_id", -1)])
        next_user_id = last_user['user_id'] + 1 if last_user else 1

        # Insert the new user
        new_user = {
            "user_id": next_user_id,
            "username": username,
            "password": hashed_password,
            "role": role
        }
        users_collection.insert_one(new_user)

        return jsonify({"status": "success", "message": "User added successfully"}), 201

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/v1/admin/getUser/<int:user_id>', methods=['POST'])
def admin_get_user(user_id):
    data = request.json
    admin_id = data.get('admin_id')

    if not admin_id:
        return jsonify({"error": "Admin ID is required"}), 400

    db = get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        users_collection = db['Users']

        # Check if the requesting user has admin permissions
        admin_user = users_collection.find_one({"user_id": admin_id})
        if not admin_user or admin_user.get("role") != "admin":
            return jsonify({"error": "Invalid Permissions"}), 403

        # Fetch the user details
        user = users_collection.find_one({"user_id": user_id}, {"_id": 0, "user_id": 1, "username": 1, "role": 1})

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
def admin_update_user(user_id):
    data = request.json
    admin_id = data.get('admin_id')
    username = data.get('username')
    role = data.get('role')

    # Ensure all required fields are provided
    if not all([admin_id, username, role]):
        return jsonify({"error": "All fields are required"}), 400

    # Connect to the database
    db = get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        users_collection = db['Users']

        # Check if the requesting user has admin permissions
        admin_user = users_collection.find_one({"user_id": admin_id})
        if not admin_user or admin_user.get("role") != "admin":
            return jsonify({"error": "Invalid Permissions"}), 403

        # Retrieve the user being updated to check the current role
        user = users_collection.find_one({"user_id": user_id})
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Check if the update involves changing the role from "user" to "admin"
        current_role = user.get("role")
        if current_role == "adopter" and role == "admin":
            # Log or notify about the privilege escalation for audit purposes (optional)
            print(f"Escalating privileges for user_id {user_id} from 'adopter' to 'admin'.")

        # Update the user information, including the role
        result = users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"username": username, "role": role}}
        )

        # Check if any document was modified
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
def admin_get_applications():
    data = request.json
    admin_id = data.get('admin_id')

    if not admin_id:
        return jsonify({"error": "Admin ID is required"}), 400

    db = get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        users_collection = db['Users']
        applications_collection = db['Applications']
        pets_info_collection = db['Pets_Info']

        # Check if the requesting user has admin permissions
        admin_user = users_collection.find_one({"user_id": admin_id})
        if not admin_user or admin_user.get("role") != "admin":
            return jsonify({"error": "Invalid Permissions"}), 403

        # Aggregate data from Applications, Users, and Pets_Info collections
        applications = list(applications_collection.aggregate([
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
            # Unwind user_info and pet_info arrays
            {"$unwind": "$user_info"},
            {"$unwind": "$pet_info"},
            # Project only the needed fields
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
        ]))

        # Convert ObjectId fields to strings
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
def admin_get_application_detail(application_id):
    data = request.json
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    db = get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        users_collection = db['Users']
        applications_collection = db['Applications']
        pets_info_collection = db['Pets_Info']

        # Check if the requesting user has admin permissions
        admin_user = users_collection.find_one({"user_id": user_id})
        if not admin_user or admin_user.get("role") != "admin":
            return jsonify({"error": "Invalid Permissions"}), 403

        # Aggregate data from Applications, Users, and Pets_Info collections
        application_detail = list(applications_collection.aggregate([
            {"$match": {"application_id": application_id}},  # Match specific application ID
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
        ]))

        # Handle case if no application is found
        if not application_detail:
            return jsonify({
                "status": "error",
                "message": "Application not found"
            }), 404
        
        # Convert MongoDB's date to ISO format
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
def update_application_status(application_id):
    data = request.json
    print(data)
    new_status = data.get('status')
    admin_id = data.get('user_id')  # Admin ID
    applicant_id = data.get('applicant_id')  # Applicant's user ID
    pet_id = data.get('pet_id')

    db = get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        users_collection = db['Users']
        applications_collection = db['Applications']
        adoptions_collection = db['Adoptions']
        pets_info_collection = db['Pets_Info']

        # Check if the requesting user has admin permissions
        admin_user = users_collection.find_one({"user_id": admin_id})
        if not admin_user or admin_user.get("role") != "admin":
            return jsonify({"error": "Invalid Permissions"}), 403

        # Update the application status
        update_result = applications_collection.update_one(
            {"application_id": application_id},
            {"$set": {"status": new_status}}
        )

        if update_result.matched_count == 0:
            return jsonify({"error": "Application not found"}), 404

        # If the status is approved, insert a new record into Adoptions
        if new_status == 'approved':
            # Update pet's adoption_status to "Unavailable"
            pets_info_collection.update_one(
                {"pet_id": pet_id},
                {"$set": {"adoption_status": "Unavailable"}}
            )
            
            # Find the current maximum adoption_id
            last_adoption = adoptions_collection.find_one(sort=[("adoption_id", -1)])
            next_adoption_id = last_adoption["adoption_id"] + 1 if last_adoption else 1

            # Define the adoption date in the desired ISO format
            today = datetime.now().isoformat()
            # Insert a new record into Adoptions collection
            adoption_data = {
                "adoption_id": next_adoption_id,
                "application_id": application_id,
                "adoption_date": datetime.fromisoformat(today.replace("Z", "+00:00")),
                "pet_id": pet_id,
                "user_id": applicant_id  # Correct user ID
                
            }
            adoptions_collection.insert_one(adoption_data)

        return jsonify({
            "status": "success",
            "message": "Application status updated successfully"
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/api/v1/admin/getAdoptions', methods=['POST'])
def admin_get_adoptions():
    data = request.json
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    db = get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        users_collection = db['Users']
        adoptions_collection = db['Adoptions']
        pets_info_collection = db['Pets_Info']
        applications_collection = db['Applications']

        # Check if the requesting user has admin permissions
        admin_user = users_collection.find_one({"user_id": user_id})
        if not admin_user or admin_user.get("role") != "admin":
            return jsonify({"error": "Invalid Permissions"}), 403

        # Aggregate data from Adoptions, Users, Pets_Info, and Applications collections
        adoptions = list(adoptions_collection.aggregate([
            # Lookup adopter details from Users collection
            {
                "$lookup": {
                    "from": "Users",
                    "localField": "user_id",
                    "foreignField": "user_id",
                    "as": "adopter_info"
                }
            },
            {"$unwind": "$adopter_info"},  # Unwind the result to flatten the array

            # Lookup pet details from Pets_Info collection
            {
                "$lookup": {
                    "from": "Pets_Info",
                    "localField": "pet_id",
                    "foreignField": "pet_id",
                    "as": "pet_info"
                }
            },
            {"$unwind": "$pet_info"},  # Unwind the result to flatten the array

            # Lookup application details from Applications collection
            {
                "$lookup": {
                    "from": "Applications",
                    "localField": "application_id",
                    "foreignField": "application_id",
                    "as": "application_info"
                }
            },
            {"$unwind": "$application_info"},  # Unwind the result to flatten the array

            # Project only the fields needed for the response
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
            # Sort by adoption_date in descending order
            {"$sort": {"adoption_date": -1}}
        ]))

        # Convert ObjectId fields and datetime to strings for JSON serialization
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
    app.run(debug=True)



# Docker
# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5000)