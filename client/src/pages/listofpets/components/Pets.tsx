import { IoMdArrowDropdown } from "react-icons/io";
import { useState, useEffect } from "react";
import PetCard from "./PetCard";
import Loader from "../../general/Loader.tsx";

export default function Pets(): JSX.Element {
  const [pets, setPets] = useState<any>([]);
  const [togglePetConditions, setTogglePetConditions] = useState<any>({
    toggle: false,
    data: {},
  });
  const [loading, setLoading] = useState(true);

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

  async function getPets() {
    setLoading(true);
    try {
      const response = await fetch("http://127.0.0.1:5000/api/v1/getPets");
      const data = await response.json();
      console.log("Fetched pets data:", data);
      setPets(data);
    } catch (error) {
      console.error("Error fetching pets:", error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    getPets();
  }, []);

  return (
    <section className="w-screen h-screen flex justify-center items-center text-gray-700">
      {loading && <Loader message="Fetching pets..." />}

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

      <div className="w-11/12 border-2 h-4/5 bg-white rounded-lg flex flex-col items-center p-4">
        <div className="flex flex-row w-full items-center justify-between relative">
          <h1 className="font-bold text-2xl border-b-4 border-gray-700 text-center">
            List Of Pets
          </h1>
        </div>
        <div
          className="w-full mt-4 pl-6 pr-6 h-full flex flex-row flex-wrap justify-evenly overflow-y-scroll overflow-x-hidden"
        >
          {pets.length > 0 ? (
            pets.map((pet: any) => (
              <PetCard
                petDetails={pet}
                setTogglePetConditions={setTogglePetConditions}
                key={pet.pet_id}
              />
            ))
          ) : (
            <div className="w-full h-full text-center text-xl font-bold">
              No Pets Available
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
