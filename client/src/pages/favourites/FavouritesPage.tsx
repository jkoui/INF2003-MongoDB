import NavBar from "../general/NavBar";
import { useEffect, useState } from "react";
import PetCard from "../listofpets/components/PetCard";
import Loader from "../general/Loader.tsx";

export default function FavouritesPage(): JSX.Element {
  const [favouritedPets, setFavouritedPets] = useState<any[]>([]);
  const [reservedPets, setReservedPets] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [togglePetConditions, setTogglePetConditions] = useState<any>({
    toggle: false,
    data: {},
  });
  useEffect(() => {
    getFavourites();
    getReservedPets();
  }, []);

  const formatDate = (dateString: string) => {
    if (!dateString) return "N/A";
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-GB', {
      weekday: 'short',
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    }).format(date);
  };
  
  async function getFavourites() {
    setLoading(true);
    try {
      const user = JSON.parse(sessionStorage.getItem("user") || "{}");
      const response = await fetch(
        `http://127.0.0.1:5000/api/v1/getFavourites?user_id=${user.user_id}`,
        {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
          },
        }
      );
      const data = await response.json();
      setFavouritedPets(data);
    } catch (error) {
      console.error("Error fetching favourite pets:", error);
    } finally {
      setLoading(false);
    }
  }

  async function getReservedPets() {
    try {
      const user = JSON.parse(sessionStorage.getItem("user") || "{}");
      const response = await fetch(
        `http://127.0.0.1:5000/api/v1/getReservedPets?user_id=${user.user_id}`,
        {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
          },
        }
      );
      const data = await response.json();
      setReservedPets(data);
    } catch (error) {
      console.error("Error fetching reserved pets:", error);
    }
  }

  // function setTogglePetConditions(conditions: any) {
  //   // Implement the logic for toggling pet conditions if needed
  //   console.log("Toggle pet conditions:", conditions);
  // }

  return (
    <div className="h-screen w-screen">
      <NavBar />

      {loading && <Loader message="Fetching your favourite pets..." />}
      
      {togglePetConditions.toggle && (
        <section className="w-screen h-screen fixed flex justify-center items-center backdrop-blur-sm z-50">
          <div className="h-5/6 shadow-2xl rounded-lg bg-white">
            <div className="h-3/6 border-b-2">
              <img
                className="w-full h-full object-contain"
                src={togglePetConditions.data.image}
                alt={togglePetConditions.data.name}
              />
            </div>
            <div className="flex flex-col h-3/6 justify-evenly p-4 tracking-wide overflow-y-auto overflow-x-hidden break-words">
              <button
                className="bg-blue-500 text-white px-4 py-2 rounded-lg transition ease-in-out hover:scale-110 hover:bg-indigo-500 duration-300"
                onClick={() => setTogglePetConditions({ toggle: false, data: {} })}
              >
                Back
              </button>
              <div className="flex flex-row mb-2">
                <p className="font-bold mr-1">Weight: </p>
                {togglePetConditions.data.condition_info?.weight || "N/A"}
              </div>
              <div className="flex flex-row mb-2">
                <p className="font-bold mr-1">Vaccination Date: </p>
                {formatDate(togglePetConditions.data.condition_info?.vaccination_date)}
              </div>
              <div className="flex flex-row mb-2">
                <p className="font-bold mr-1">Health Condition: </p>
                {togglePetConditions.data.condition_info?.health_condition || "N/A"}
              </div>
              <div className="flex flex-row mb-2">
                <p className="font-bold mr-1">Sterilisation Status: </p>
                {togglePetConditions.data.condition_info?.sterilisation_status || "N/A"}
              </div>
              <div className="flex flex-row mb-2">
                <p className="font-bold mr-1">Adoption Fee: </p>
                {togglePetConditions.data.condition_info?.adoption_fee || "N/A"}
              </div>
              <div className="flex flex-row mb-2">
                <p className="font-bold mr-1">Previous Owner: </p>
                {togglePetConditions.data.condition_info?.previous_owner || "N/A"}
              </div>
            </div>
          </div>
        </section>
      )}
      <div className="bg-white border border-gray-300 rounded-lg shadow-lg p-8 m-4">
        <h1 className="text-2xl font-bold mb-4">Your Favourite Pets</h1>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {favouritedPets.length > 0 ? (
            favouritedPets.map((pet) => (
              <PetCard
                key={pet.pet_id}
                petDetails={pet}
                setTogglePetConditions={setTogglePetConditions}
                reservedPets={reservedPets}
                favouritedPets={favouritedPets}
              />
            ))
          ) : (
            <p>You have no favourite pets yet.</p>
          )}
        </div>
      </div>
    </div>
  );
}