import { useState, useEffect } from "react";

export default function PetCard({
  petDetails,
  setTogglePetConditions,
  favouritedPets = [],
  reservedPets = [],
}: any): JSX.Element {
  const [isFavourite, setIsFavourite] = useState<boolean>(false);
  const [isReserved, setIsReserved] = useState<boolean>(false);

  useEffect(() => {
    const isAlreadyFavourite = favouritedPets.some(
      (favPet: any) => favPet.pet_id === petDetails.pet_id
    );
    setIsFavourite(isAlreadyFavourite);
  }, [favouritedPets, petDetails]);

  useEffect(() => {
    const isPetReserved = reservedPets.some(
      (reservedPet: any) => reservedPet.pet_id === petDetails.pet_id
    );
    setIsReserved(isPetReserved);
  }, [reservedPets, petDetails]);

  const handleAddToFavourites = async () => {
    const userSession: any = sessionStorage.getItem("user");
    const user = JSON.parse(userSession);
    if (!user) {
      alert("You need to log in to add pets to favourites.");
      return;
    }

    try {
      const response = await fetch("http://127.0.0.1:5000/api/v1/addFavourite", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          pet_id: petDetails.pet_id,
          user_id: user.user_id,
        }),
      });

      if (response.status === 201) {
        setIsFavourite(true);
        alert(`${petDetails.name} has been added to your favourites.`);
      } else {
        const data = await response.json();
        alert(data.error || "Failed to add to favourites.");
      }
    } catch (error) {
      console.error("Error adding pet to favourites:", error);
      alert("An error occurred while adding to favourites.");
    }
  };

  async function reservePet() {
    const user: any = sessionStorage.getItem("user");
    const response = await fetch("http://127.0.0.1:5000/api/v1/addtocart", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        pet_id: petDetails.pet_id,
        user_id: JSON.parse(user).user_id,
      }),
    });

    if (response.status === 200) {
      alert(`${petDetails.name} has been added to cart.`);
      setIsReserved(true);
    } else {
      const data = await response.json();
      alert(data.error || `${petDetails.name} is already in your cart.`);
    }
  }

  return (
    <article className="w-96 h-full border-2 rounded-lg shadow-xl mb-4">
      <div className="w-full h-2/6 border-b-2">
        <img
          className="w-full h-full object-cover"
          src={petDetails.image}
          alt={petDetails.name}
        />
      </div>

      <div className="flex flex-col h-3/6 justify-evenly p-4 tracking-wide overflow-y-auto overflow-x-hidden break-words">
        <div className="flex flex-row mb-2">
          <p className="font-bold mr-1">Pet ID:</p> {petDetails.pet_id}
        </div>
        <div className="flex flex-row mb-2">
          <p className="text-2xl italic underline font-bold mr-1">
            {petDetails.name}
          </p>
        </div>
        <div className="flex flex-row mb-2">
          <p className="font-bold mr-1">Type: </p> {petDetails.type}
        </div>
        <div className="flex flex-row mb-2">
          <p className="font-bold mr-1">Breed: </p> {petDetails.breed}
        </div>
        <div className="flex flex-row mb-2">
          <p className="font-bold mr-1">Gender: </p> {petDetails.gender}
        </div>
        <div className="flex flex-row mb-2">
          <p className="font-bold mr-1">Age: </p> {petDetails.age_month} months
        </div>
        <div className="flex flex-row mb-2">
          <p className="font-bold mr-1">Adoption Status: </p> {petDetails.adoption_status}
        </div>
        <p>{petDetails.description}</p>
      </div>

      <div className="flex flex-row h-1/6 justify-between items-center space-x-4 p-4 border-t-2">
        <button
          className="bg-blue-500 text-white px-4 py-2 rounded-lg transition ease-in-out hover:scale-110 hover:bg-indigo-500 duration-300"
          onClick={() => {
            setTogglePetConditions({
              toggle: true,
              data: {
                ...petDetails,
                condition_info: petDetails.condition_info || {}, // Fallback for condition_info
              },
            });
          }}
        >
          View Pet Conditions
        </button>
        
        <button
          className={`bg-blue-500 text-white px-4 py-2 rounded-lg transition ease-in-out hover:scale-110 hover:bg-indigo-500 duration-300 ${
            isReserved || petDetails.adoption_status === "Unavailable"
              ? "opacity-50 cursor-not-allowed"
              : ""
          }`}
          onClick={() => {
            if (!isReserved && petDetails.adoption_status !== "Unavailable") {
              reservePet();
            }
          }}
          disabled={isReserved || petDetails.adoption_status === "Unavailable"}
        >
          {isReserved || petDetails.adoption_status === "Unavailable"
            ? "Unavailable for Adoption"
            : "Reserve Pet"}
        </button>

        <button
          className={`${isFavourite ? "bg-gray-500" : "bg-red-500"} text-white px-4 py-2 rounded-lg transition ease-in-out hover:scale-110 hover:bg-indigo-500 duration-300`}
          onClick={() => handleAddToFavourites()}
          disabled={isFavourite}
        >
          {isFavourite ? "Added to Favourites" : "Add to Favourites"}
        </button>
      </div>
    </article>
  );
}
