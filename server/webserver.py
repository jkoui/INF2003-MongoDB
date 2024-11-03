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
            "user": {"user_id": str(user['_id']), "username": user['username'], "role": user['role']}
        }), 200
    else:
        return jsonify({"error": "Invalid username or password"}), 401

# working (done)
@app.route('/api/v1/getPets', methods=['GET'])
def get_all_pets():
    # Connect to the database
    db = get_db_connection()

    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    # Define collections
    pet_info_collection = db['Pets_Info']

    # Define the aggregation pipeline
    pipeline = [
        {
            "$lookup": {
                "from": "Pet_Condition",
                "localField": "pet_condition_id",
                "foreignField": "_id",
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

    # Run the aggregation pipeline
    pets = list(pet_info_collection.aggregate(pipeline))

    # Convert ObjectIds to strings for JSON serialization
    for pet in pets:
        pet['_id'] = str(pet['_id'])
        if pet.get('condition_info') and '_id' in pet['condition_info']:
            pet['condition_info']['_id'] = str(pet['condition_info']['_id'])

    # Return JSON response
    return jsonify(pets), 200
 
 #working (done)
@app.route('/api/v1/getTop3', methods=['GET'])
def get_top3():
    db = get_db_connection()  # Assuming this returns a MongoDB client with the target database

    if db is None:
        return jsonify([]), 500  # Return an empty array in case of failure

    try:
        # Use aggregation to join, group, and sort
        top3_pets = list(db['Pets_Info'].aggregate([
            {
                "$lookup": {
                    "from": "Favourites",        # Join with Favourites collection
                    "localField": "pet_id",      # Field in Pet_Info collection
                    "foreignField": "pet_id",    # Field in Favourites collection
                    "as": "favourites"           # Resulting array field name
                }
            },
            {
                "$addFields": {
                    "favourite_count": {"$size": "$favourites"}  # Count the number of favorites
                }
            },
            {
                "$sort": {"favourite_count": -1}  # Sort by favourite_count in descending order
            },
            {
                "$limit": 3  # Limit to top 3
            },
            {
                "$project": {
                    "favourites": 0  # Exclude the favourites array from the final output
                }
            }
        ]))

        # Convert ObjectId fields to strings
        for pet in top3_pets:
            if '_id' in pet:
                pet['_id'] = str(pet['_id'])

        return jsonify(top3_pets), 200  # Return the JSON response

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/addFavourite', methods=['POST'])
def addFavourite():
    db = get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    data = request.json
    pet_id = data.get('pet_id')
    user_id = data.get('user_id')

    if not pet_id or not user_id:
        return jsonify({"error": "Pet ID and User ID are required"}), 400

    # Convert pet_id to ObjectId if it's a valid integer
    if isinstance(pet_id, int):
        pet_id = str(pet_id)  # Convert to string for ObjectId compatibility

    # Wrap pet_id in ObjectId if it's a string
    try:
        pet_id = ObjectId(pet_id)
    except Exception as e:
        return jsonify({"error": f"Invalid pet_id format: {e}"}), 400

    favourites_collection = db['Favourites']

    # Check if the pet is already in favourites
    existing_favourite = favourites_collection.find_one({"user_id": user_id, "pet_id": pet_id})
    if existing_favourite:
        return jsonify({"error": "Pet is already in favourites"}), 400

    # Add to favourites
    favourites_collection.insert_one({"user_id": user_id, "pet_id": pet_id})
    return jsonify({"message": "Pet added to favourites successfully"}), 201
    
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


@app.route('/api/v1/getFavourites', methods=['GET'])
def getFavourites():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    db = get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$lookup": {
            "from": "Pets_Info",
            "localField": "pet_id",
            "foreignField": "_id",
            "as": "pets_info"
        }},
        {"$unwind": "$pets_info"}
    ]

    favourited_pets = list(db["Favourites"].aggregate(pipeline))

    # Convert ObjectIds to strings for JSON compatibility
    for pet in favourited_pets:
        pet['_id'] = str(pet['_id'])
        pet['pets_info']['_id'] = str(pet['pets_info']['_id'])

    # Return only the pet_info details
    return jsonify([pet['pets_info'] for pet in favourited_pets]), 200
