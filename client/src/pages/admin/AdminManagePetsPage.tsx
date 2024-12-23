import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Loader from "../general/Loader";
import AdminNavBar from "./AdminNavbar";
import PetCardAdmin from "./PetCardAdmin";

export default function AdminManagePetsPage() {
  const navigate = useNavigate();
  const [pets, setPets] = useState<any>([])
  const [loading, setLoading] = useState(true);
  const [togglePetConditions, setTogglePetConditions] = useState<any>({
    toggle: false,
    data: {},
  });
  const [editPetToggle, setEditPetToggle] = useState<any>({
    toggle: false,
    data: {},
  })
  const [toggleAddPet, setToggleAddPet] = useState<any>({
    toggle: false,
    data: {},
  })


  async function getPets() {
    setLoading(true);
    try {
      const response = await fetch("http://127.0.0.1:5000/api/v1/getPets");
      const data = await response.json();
      setPets(data);
    } catch (error) {
      console.error("Error fetching pets:", error);
    } finally {
      setLoading(false);
    }
  }

  const handleInputChange = (e: any) => {
    const { name, value } = e.target;
    setEditPetToggle((prevState: any) => ({
      ...prevState,
      data: {
        ...prevState.data,
        [name]: value,
      },
    }));
  };

  const handleInputChangeAdd = (e: any) => {
    const { name, value } = e.target;
    let formattedValue = value;
  
    if (name === "vaccination_date") {
      const date = new Date(value);
      formattedValue = date.toISOString().slice(0, 16);  // Converts to "YYYY-MM-DDTHH:mm:ss.sssZ"
    }
  
    setToggleAddPet((prevState: any) => ({
      ...prevState,
      data: { ...prevState.data, [name]: formattedValue },
    }));
  };



  async function addPet(e:any, petData: any) {
    e.preventDefault()
    const userSession: any = sessionStorage.getItem("user")
    const user = JSON.parse(userSession);

    try {
      const response = await fetch(
        "http://127.0.0.1:5000/api/v1/admin/addPet",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ pet_data: petData, user_id: user.user_id }),
        }
      );

      if (response.status === 200) {
        alert(`${petData.name} has been added.`);
        setToggleAddPet((prevState: any) => ({
          ...prevState,
          toggle: false
        }))
        getPets()

      } else {
        const data = await response.json();
        alert(data.error || "Failed to add pet.");
      }
    } catch (error) {
      console.error("Error adding pet:", error);
      alert("An error occurred while adding pet.");
    }

    setToggleAddPet((prevState: any) => ({
      ...prevState,
      toggle: false
    }))
  }

  async function editPet(e: any, petData: any) {
    e.preventDefault()

    const userSession: any = sessionStorage.getItem("user")
    const user = JSON.parse(userSession);

    try {
      const response = await fetch(
        "http://127.0.0.1:5000/api/v1/admin/editPet",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ pet_data: petData, user_id: user.user_id }),
        }
      );

      if (response.status === 200) {
        alert(`${editPetToggle.data.name} has been updated.`);
        getPets()
      } else {
        const data = await response.json();
        alert(data.error || "Failed to update.");
      }
    } catch (error) {
      console.error("Error updating pet:", error);
      alert("An error occurred while updating pet.");
    }

    setEditPetToggle((prevState: any) => ({
      ...prevState,
      toggle: false
    }))
  }
  
  useEffect(() => {
    const user: any = sessionStorage.getItem("user");

    const parsedUser = JSON.parse(user);
    if (parsedUser.role !== "admin") {
      navigate("/")
    }

    getPets()
  }, []);


  return (
    <>
      <AdminNavBar/>
      <section className="w-full h-screen flex justify-center items-center text-gray-700 overflow-x-hidden">
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
                onClick={() =>
                  setTogglePetConditions({ toggle: false, data: {} })
                }
              >
                Back
              </button>
              <div className="flex flex-row mb-2">
                <p className="font-bold mr-1">Weight: </p>
                {togglePetConditions.data.condition_info.weight}
              </div>
              <div className="flex flex-row mb-2">
                <p className="font-bold mr-1">Vaccination Date: </p>
                {togglePetConditions.data.condition_info.vaccination_date}
              </div>
              <div className="flex flex-row mb-2">
                <p className="font-bold mr-1">Health Condition: </p>
                {togglePetConditions.data.condition_info.health_condition}
              </div>
              <div className="flex flex-row mb-2">
                <p className="font-bold mr-1">Sterilisation Status: </p>
                {togglePetConditions.data.condition_info.sterilisation_status}
              </div>
              <div className="flex flex-row mb-2">
                <p className="font-bold mr-1">Adoption Fee: </p>
                {togglePetConditions.data.condition_info.adoption_fee}
              </div>
              <div className="flex flex-row mb-2">
                <p className="font-bold mr-1">Previous Owner: </p>
                {togglePetConditions.data.condition_info.previous_owner}
              </div>
            </div>
          </div>
        </section>
      )}

      {toggleAddPet.toggle && <section className="w-screen h-screen fixed flex justify-center items-center backdrop-blur-sm z-50">
          <div className="h-5/6 w-5/6 shadow-2xl rounded-lg bg-white">
            <div className="h-3/6 w-full border-b-2 flex justify-center items-center cursor:pointer">
              Fill in Image Link
            </div>
            <div className="flex flex-col h-3/6 justify-evenly p-4 tracking-wide overflow-y-auto overflow-x-hidden break-words">
              <button
                className="bg-blue-500 text-white px-4 py-2 rounded-lg transition ease-in-out hover:scale-110 hover:bg-indigo-500 duration-300"
                onClick={() =>
                  setToggleAddPet({
                    toggle: false,
                    data: {},
                  })
                }
              >
                Back
              </button>
              <form onSubmit={(e: any) => {addPet(e, toggleAddPet.data)}} className="mt-2 mb-2">
              <div className="flex flex-row mb-2">
                    <p className="font-bold mr-1">Image Link: </p>
                    <input className="border-2 rounded-lg pl-2 pr-2 border-black tracking-wide" name="image" value={toggleAddPet.data.image} onChange={(e: any) => {handleInputChangeAdd(e)}}/>
                  </div>
                <div className="flex flex-row mb-2">
                    <p className="font-bold mr-1">Name: </p>
                    <input className="border-2 rounded-lg pl-2 pr-2 border-black tracking-wide" name="name" value={toggleAddPet.data.name} onChange={(e: any) => {handleInputChangeAdd(e)}}/>
                  </div>
                  <div className="flex flex-row mb-2">
                    <p className="font-bold mr-1">Type: </p>
                    <select
                        className="border-2 rounded-lg pl-2 pr-2 border-black tracking-wide"
                        name="type"
                        value={toggleAddPet.data.type}
                        onChange={(e: any) => handleInputChangeAdd(e)}
                      >
                        <option value="">Choose one</option>
                        <option value="Rabbit">Rabbit</option>
                        <option value="Dog">Dog</option>
                        <option value="Cat">Cat</option>
                        <option value="Bird">Bird</option>
                    </select>
                  </div>
                  <div className="flex flex-row mb-2">
                    <p className="font-bold mr-1">Breed: </p>
                    <input className="border-2 rounded-lg pl-2 pr-2 border-black tracking-wide" name="breed" value={toggleAddPet.data.breed} onChange={(e: any) => {handleInputChangeAdd(e)}}/>
                  </div>
                  <div className="flex flex-row mb-2">
                    <p className="font-bold mr-1">Gender: </p>
                    <select
                      className="border-2 rounded-lg pl-2 pr-2 border-black tracking-wide"
                      name="gender"
                      value={toggleAddPet.data.gender}
                      onChange={(e: any) => handleInputChangeAdd(e)}
                    >
                      <option value="">Choose one</option>
                      <option value="Male">Male</option>
                      <option value="Female">Female</option>
                    </select>
                  </div>
                  <div className="flex flex-row mb-2">
                    <p className="font-bold mr-1">Age: </p>
                    <input className="border-2 rounded-lg pl-2 pr-2 border-black tracking-wide" name="age_month" value={toggleAddPet.data.age_month} onChange={(e: any) => {handleInputChangeAdd(e)}}/>
                  </div>
                  <div className="flex flex-row mb-2">
                    <p className="font-bold mr-1">Description: </p>
                    <input className="border-2 rounded-lg pl-2 pr-2 border-black tracking-wide" name="description" value={toggleAddPet.data.description} onChange={(e: any) => {handleInputChangeAdd(e)}}/>
                  </div>
                  <div className="flex flex-row mb-2">
                    <p className="font-bold mr-1">Weight: </p>
                    <input className="border-2 rounded-lg pl-2 pr-2 border-black tracking-wide" name="weight" value={toggleAddPet.data.weight} onChange={(e: any) => {handleInputChangeAdd(e)}}/>
                  </div>
                  <div className="flex flex-row mb-2">
                    <p className="font-bold mr-1">{"Vaccination Date (dd/mm/yyyy):"} </p>
                    <input type="datetime-local" className="border-2 rounded-lg pl-2 pr-2 border-black tracking-wide" name="vaccination_date" value={toggleAddPet.data.vaccination_date} onChange={(e: any) => {handleInputChangeAdd(e)}}/>
                  </div>
                  <div className="flex flex-row mb-2">
                    <p className="font-bold mr-1">Health Condition: </p>
                    <input className="border-2 rounded-lg pl-2 pr-2 border-black tracking-wide" name="health_condition" value={toggleAddPet.data.health_condition} onChange={(e: any) => {handleInputChangeAdd(e)}}/>
                  </div>
                  <div className="flex flex-row mb-2">
                    <p className="font-bold mr-1">Sterilisation Status: </p>
                    <input className="border-2 rounded-lg pl-2 pr-2 border-black tracking-wide" name="sterilisation_status" value={toggleAddPet.data.sterilisation_status} onChange={(e: any) => {handleInputChangeAdd(e)}}/>
                  </div>
                  <div className="flex flex-row mb-2">
                    <p className="font-bold mr-1">Adoption Fee: </p>
                    <input className="border-2 rounded-lg pl-2 pr-2 border-black tracking-wide" name="adoption_fee" value={toggleAddPet.data.adoption_fee} onChange={(e: any) => {handleInputChangeAdd(e)}}/>
                  </div>
                  <div className="flex flex-row mb-2">
                    <p className="font-bold mr-1">Previous Owner: </p>
                    <input className="border-2 rounded-lg pl-2 pr-2 border-black tracking-wide" name="previous_owner" value={toggleAddPet.data.previous_owner} onChange={(e: any) => {handleInputChangeAdd(e)}}/>
                  </div>
              </form>
              <button
                className="bg-blue-500 text-white px-4 py-2 rounded-lg transition ease-in-out hover:scale-110 hover:bg-indigo-500 duration-300"
                onClick={(e: any) =>
                  addPet(e, toggleAddPet.data)
                }
              >
                Add Pet
              </button>
            </div>
          </div>
        </section>}

      {editPetToggle.toggle && <section className="w-screen h-screen fixed flex justify-center items-center backdrop-blur-sm z-50">
          <div className="h-5/6 w-5/6 shadow-2xl rounded-lg bg-white">
            <div className="h-3/6 border-b-2">
              <img
                className="w-full h-full object-contain"
                src={editPetToggle.data.image}
                alt={editPetToggle.data.name}
              />
            </div>
            <div className="flex flex-col h-3/6 justify-evenly p-4 tracking-wide overflow-y-auto overflow-x-hidden break-words">
              <button
                className="bg-blue-500 text-white px-4 py-2 rounded-lg transition ease-in-out hover:scale-110 hover:bg-indigo-500 duration-300"
                onClick={() =>
                  setEditPetToggle({
                    toggle: false,
                    data: {},
                  })
                }
              >
                Back
              </button>
              <form onSubmit={(e: any) => {editPet(e, editPetToggle.data)}} className="mt-2 mb-2">
                <div className="flex flex-row mb-2">
                    <p className="font-bold mr-1">Name: </p>
                    <input className="border-2 rounded-lg pl-2 pr-2 border-black tracking-wide" name="name" value={editPetToggle.data.name} onChange={(e: any) => {handleInputChange(e)}}/>
                  </div>
                  <div className="flex flex-row mb-2">
                    <p className="font-bold mr-1">Type: </p>
                    <select
                        className="border-2 rounded-lg pl-2 pr-2 border-black tracking-wide"
                        name="type"
                        value={editPetToggle.data.type}
                        onChange={(e: any) => handleInputChange(e)}
                      >
                        <option value="">Choose one</option>
                        <option value="Rabbit">Rabbit</option>
                        <option value="Dog">Dog</option>
                        <option value="Cat">Cat</option>
                        <option value="Bird">Bird</option>
                    </select>
                    </div>
                  <div className="flex flex-row mb-2">
                    <p className="font-bold mr-1">Breed: </p>
                    <input className="border-2 rounded-lg pl-2 pr-2 border-black tracking-wide" name="breed" value={editPetToggle.data.breed} onChange={(e: any) => {handleInputChange(e)}}/>
                  </div>
                  <div className="flex flex-row mb-2">
                    <p className="font-bold mr-1">Gender: </p>
                    <select
                      className="border-2 rounded-lg pl-2 pr-2 border-black tracking-wide"
                      name="gender"
                      value={editPetToggle.data.gender}
                      onChange={(e: any) => handleInputChange(e)}
                    >
                      <option value="">Choose one</option>
                      <option value="Male">Male</option>
                      <option value="Female">Female</option>
                    </select>                  </div>
                  <div className="flex flex-row mb-2">
                    <p className="font-bold mr-1">Age: </p>
                    <input className="border-2 rounded-lg pl-2 pr-2 border-black tracking-wide" name="age_month" value={editPetToggle.data.age_month} onChange={(e: any) => {handleInputChange(e)}}/>
                  </div>
                  <div className="flex flex-row mb-2">
                    <p className="font-bold mr-1">Description: </p>
                    <input className="border-2 rounded-lg pl-2 pr-2 border-black tracking-wide" name="description" value={editPetToggle.data.description} onChange={(e: any) => {handleInputChange(e)}}/>
                  </div>
                  <div className="flex flex-row mb-2">
                    <p className="font-bold mr-1">Weight: </p>
                    <input className="border-2 rounded-lg pl-2 pr-2 border-black tracking-wide" name="weight" value={editPetToggle.data.weight} onChange={(e: any) => {handleInputChange(e)}}/>
                  </div>
                  <div className="flex flex-row mb-2">
                    <p className="font-bold mr-1">Vaccination Date: </p>
                    <input className="border-2 rounded-lg pl-2 pr-2 border-black tracking-wide" name="vaccination_date" value={editPetToggle.data.vaccination_date} onChange={(e: any) => {handleInputChange(e)}}/>
                  </div>
                  <div className="flex flex-row mb-2">
                    <p className="font-bold mr-1">Health Condition: </p>
                    <input className="border-2 rounded-lg pl-2 pr-2 border-black tracking-wide" name="health_condition" value={editPetToggle.data.health_condition} onChange={(e: any) => {handleInputChange(e)}}/>
                  </div>
                  <div className="flex flex-row mb-2">
                    <p className="font-bold mr-1">Sterilisation Status: </p>
                    <input className="border-2 rounded-lg pl-2 pr-2 border-black tracking-wide" name="sterilisation_status" value={editPetToggle.data.sterilisation_status} onChange={(e: any) => {handleInputChange(e)}}/>
                  </div>
                  <div className="flex flex-row mb-2">
                    <p className="font-bold mr-1">Adoption Fee: </p>
                    <input className="border-2 rounded-lg pl-2 pr-2 border-black tracking-wide" name="adoption_fee" value={editPetToggle.data.adoption_fee} onChange={(e: any) => {handleInputChange(e)}}/>
                  </div>
                  <div className="flex flex-row mb-2">
                    <p className="font-bold mr-1">Previous Owner: </p>
                    <input className="border-2 rounded-lg pl-2 pr-2 border-black tracking-wide" name="previous_owner" value={editPetToggle.data.previous_owner} onChange={(e: any) => {handleInputChange(e)}}/>
                  </div>
              </form>
              <button
                className="bg-blue-500 text-white px-4 py-2 rounded-lg transition ease-in-out hover:scale-110 hover:bg-indigo-500 duration-300"
                onClick={(e: any) =>
                  editPet(e, editPetToggle.data)
                }
              >
                Edit Pet
              </button>
            </div>
          </div>
        </section>}
      <div className="w-11/12 border-2 h-4/5 bg-white rounded-lg flex flex-col items-center p-4">
        <div className="flex flex-row w-full items-center justify-center relative">
          <h1 className="font-bold text-2xl border-b-4 border-gray-700 text-center">
            Manage Pets
          </h1>
        </div>
        <button
          className="bg-blue-500 text-white px-4 py-2 rounded-lg transition ease-in-out hover:scale-110 hover:bg-indigo-500 duration-300 mt-4 w-full"
          onClick={() =>
            setToggleAddPet({ toggle: true, data: {} })
          }
        >
          Add Pet
        </button>
        <div
          className="w-full mt-4 pl-6 pr-6 h-full flex flex-row flex-wrap justify-evenly overflow-y-scroll overflow-x-hidden"
        >
          {pets.length > 0 ? (
            pets.map((pet: any) => {
              return (
                <PetCardAdmin
                  petDetails={pet}
                  setTogglePetConditions={setTogglePetConditions}
                  setEditPetToggle={setEditPetToggle}
                  setPets={setPets}
                  pets={pets}
                  key={pet.pet_id}
                />
              );
            })
          ) : (
            <div className="w-full h-full text-center text-xl font-bold">
              No Pets Available
            </div>
          )}
        </div>
      </div>
    </section>
    </>
  )
}

