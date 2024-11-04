from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime
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
