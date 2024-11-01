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
        user_collection.insert_one({
            "username": username,
            "password": hashed_password,
            "role": "adopter"
        })
        return jsonify({"message": "User registered successfully"}), 201

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
 
@app.route('/api/v1/getTop3', methods=['GET'])
def get_Top3():
    db = get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # Collection references
        favourites_collection = db['Favourites']
        pets_info_collection = db['Pets_Info']

        # Automatically convert pet_id in Favourites to ObjectId if necessary
        for favourite in favourites_collection.find():
            pet_id = favourite.get('pet_id')
            
            # Ensure pet_id is not already an ObjectId and is of a type that can be converted
            if pet_id and not isinstance(pet_id, ObjectId):
                try:
                    # Attempt to find a matching document in Pets_Info
                    pet_info = pets_info_collection.find_one({"_id": ObjectId(str(pet_id).zfill(24))})
                    
                    # If a matching document is found, update pet_id to ObjectId in Favourites
                    if pet_info:
                        favourites_collection.update_one(
                            {'_id': favourite['_id']},
                            {'$set': {'pet_id': ObjectId(str(pet_id).zfill(24))}}
                        )
                        print(f"Converted pet_id for document with _id {favourite['_id']} to ObjectId")
                except Exception as e:
                    print(f"Error converting pet_id for document with _id {favourite['_id']}: {e}")

        # Define the aggregation pipeline for MongoDB
        pipeline = [
            {"$lookup": {
                "from": "Pets_Info",
                "localField": "pet_id",
                "foreignField": "_id",
                "as": "pets_info"
            }},
            {"$unwind": "$pets_info"},
            {"$group": {
                "_id": "$pets_info._id",
                "favourite_count": {"$sum": 1},
                "pets_info": {"$first": "$pets_info"}
            }},
            {"$sort": {"favourite_count": -1}},
            {"$limit": 3}
        ]

        # Perform the aggregation
        top3pets = list(favourites_collection.aggregate(pipeline))
        print("Top 3 pets after aggregation:", top3pets)

        # Convert ObjectId fields to strings for compatibility with JSON
        for pet in top3pets:
            pet['_id'] = str(pet['_id'])
            pet['pets_info']['_id'] = str(pet['pets_info']['_id'])

            # Convert any other ObjectId fields (e.g., images) if they exist in pets_info
            if 'image' in pet['pets_info'] and isinstance(pet['pets_info']['image'], ObjectId):
                pet['pets_info']['image'] = str(pet['pets_info']['image'])
        
        return jsonify(top3pets), 200

    except Exception as e:
        print("Error in getTop3 aggregation:", str(e))
        return jsonify({"error": "Failed to retrieve top pets"}), 500

@app.route('/api/v1/addFavourite', methods=['POST'])
def addFavourite():
    data = request.json
    pet_id = data.get('pet_id')
    user_id = data.get('user_id')

    if not pet_id:
        return jsonify({"error": "Pet ID is required"}), 400

    db = get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    favourites_collection = db['Favourites']

    # Check if pet is already in the user's favorites
    if favourites_collection.find_one({"user_id": user_id, "pet_id": pet_id}):
        return jsonify({"error": "Pet is already in favourites"}), 400

    # Insert the favourite pet into the Favourites collection
    try:
        favourites_collection.insert_one({"user_id": user_id, "pet_id": pet_id})
        return jsonify({"message": "Pet added to favourites successfully"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/v1/getReservedPets', methods=['GET'])
def get_reserved_pets():
    db = get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # Use aggregation to join Pet_Info and Applications collections
        pipeline = [
            {"$lookup": {
                "from": "Applications",
                "localField": "_id",
                "foreignField": "pet_id",
                "as": "application_info"
            }},
            {"$match": {"application_info": {"$ne": []}}}  # Filter only pets with applications
        ]

        pet_info_collection = db['Pet_Info']
        reserved_pets = list(pet_info_collection.aggregate(pipeline))

        # Convert ObjectIds to strings
        for pet in reserved_pets:
            pet['_id'] = str(pet['_id'])

        return jsonify(reserved_pets), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/v1/getFavourites', methods=['GET'])
def getFavourites():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    db = get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # Use aggregation to join Favourites with Pet_Info based on pet_id
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$lookup": {
                "from": "Pet_Info",
                "localField": "pet_id",
                "foreignField": "_id",
                "as": "pet_info"
            }},
            {"$unwind": "$pet_info"}
        ]

        favourites_collection = db['Favourites']
        favourited_pets = list(favourites_collection.aggregate(pipeline))

        # Format each document for JSON response
        for pet in favourited_pets:
            pet['pet_info']['_id'] = str(pet['pet_info']['_id'])
            pet['_id'] = str(pet['_id'])

        # Only return pet_info field (the pet details)
        favourited_pets = [pet['pet_info'] for pet in favourited_pets]

        return jsonify(favourited_pets), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500