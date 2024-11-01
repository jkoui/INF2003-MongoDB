from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime
from pymongo.errors import DuplicateKeyError
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

@app.route('/api/v1/getPets', methods=['GET', 'OPTIONS'])
def get_all_pets():
    db = get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    pipeline = [
        {
            "$lookup": {
                "from": "Pet_Condition",            # Collection to join with
                "localField": "pet_condition_id",   # Field in Pet_Info
                "foreignField": "_id",              # Field in Pet_Condition
                "as": "condition_info"              # Output field name for joined data
            }
        },
        {
            "$unwind": {
                "path": "$condition_info",          # Unwind condition_info array
                "preserveNullAndEmptyArrays": True  # Keep pets without condition info
            }
        }
    ]

    pet_info_collection = db['Pet_Info']
    pets = list(pet_info_collection.aggregate(pipeline))

    # Convert ObjectIds to strings for JSON serialization
    for pet in pets:
        pet['_id'] = str(pet['_id'])
        if pet.get('condition_info'):
            pet['condition_info']['_id'] = str(pet['condition_info']['_id'])

    return jsonify(pets), 200
    
@app.route('/api/v1/getTop3', methods=['GET'])
def get_Top3():
    db = get_db_connection()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # Define the aggregation pipeline for MongoDB
        pipeline = [
            {"$lookup": {
                "from": "Pet_Info",
                "localField": "pet_id",
                "foreignField": "_id",
                "as": "pet_info"
            }},
            {"$unwind": "$pet_info"},
            {"$group": {
                "_id": "$pet_info._id",
                "favourite_count": {"$sum": 1},
                "pet_info": {"$first": "$pet_info"}
            }},
            {"$sort": {"favourite_count": -1}},
            {"$limit": 3}
        ]

        # Perform the aggregation
        favourites_collection = db['Favourites']
        top3pets = list(favourites_collection.aggregate(pipeline))

        # Convert ObjectId to strings for compatibility with JSON
        for pet in top3pets:
            pet['_id'] = str(pet['_id'])
            pet['pet_info']['_id'] = str(pet['pet_info']['_id'])

            # Convert any other ObjectId fields (e.g., images) if they exist in pet_info
            if 'image' in pet['pet_info'] and isinstance(pet['pet_info']['image'], ObjectId):
                pet['pet_info']['image'] = str(pet['pet_info']['image'])
        
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