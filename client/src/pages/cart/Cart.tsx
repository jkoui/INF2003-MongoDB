import NavBar from "../general/NavBar";
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Loader from "../general/Loader.tsx";

export default function Cart(): JSX.Element {
  const [cart, setCart] = useState<any>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const [togglePetConditions, setTogglePetConditions] = useState<any>({
    toggle: false,
    data: {},
  });
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

  async function getCart() {
    const user: any = sessionStorage.getItem("user");
    const user_id = JSON.parse(user).user_id;
    const response = await fetch("http://127.0.0.1:5000/api/v1/getcart", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: user_id,
      }),
    });

    const data = await response.json();
    setCart(data);
    setLoading(false)
  }

  async function removeFromCart(pet_id: any) {
    const user: any = sessionStorage.getItem("user");
    const user_id = JSON.parse(user).user_id;
    const response = await fetch(
      "http://127.0.0.1:5000/api/v1/removefromcart",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: user_id,
          pet_id: pet_id,
        }),
      }
    );

    await response.json();
    const updatedCart = cart.filter((pet: any) => pet.pet_id !== pet_id);
    setCart(updatedCart);
    alert("Successfully removed from cart!");
  }

  useEffect(() => {
    getCart();
  }, []);

  if (loading) return <Loader message="loading cart..." />

  return (
    <div className="h-screen w-screen">
      <NavBar />
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
                {togglePetConditions.data.pet_condition.weight || "N/A"}
              </div>
              <div className="flex flex-row mb-2">
                <p className="font-bold mr-1">Vaccination Date: </p>
                {formatDate(togglePetConditions.data.pet_condition.vaccination_date)}
              </div>
              <div className="flex flex-row mb-2">
                <p className="font-bold mr-1">Health Condition: </p>
                {togglePetConditions.data.pet_condition.health_condition || "N/A"}
              </div>
              <div className="flex flex-row mb-2">
                <p className="font-bold mr-1">Sterilisation Status: </p>
                {togglePetConditions.data.pet_condition.sterilisation_status || "N/A"}
              </div>
              <div className="flex flex-row mb-2">
                <p className="font-bold mr-1">Adoption Fee: </p>
                {togglePetConditions.data.pet_condition.adoption_fee || "N/A"}
              </div>
              <div className="flex flex-row mb-2">
                <p className="font-bold mr-1">Previous Owner: </p>
                {togglePetConditions.data.pet_condition.previous_owner || "N/A"}
              </div>
            </div>
          </div>
        </section>
      )}
      <section className="w-screen h-screen flex justify-center items-center text-gray-700">
        <div className="w-11/12 border-2 h-4/5 bg-white rounded-lg flex flex-col items-center p-4">
          <div className="flex flex-row w-full items-center justify-center relative">
            <h1 className="font-bold text-2xl border-b-4 border-gray-700 text-center">
              Cart
            </h1>
            {cart.length > 0 && (
              <button
                className="absolute right-0 bg-blue-500 text-white px-4 py-2 rounded-lg transition ease-in-out hover:scale-110 hover:bg-indigo-500 duration-300"
                onClick={() => {
                  navigate("/checkout", { state: { cart } });
                }}
              >
                Confirm reservation
              </button>
            )}
          </div>
          <div className="w-full mt-4 pl-6 pr-6 h-full flex flex-row flex-wrap justify-evenly overflow-y-scroll overflow-x-hidden">
            {cart.length > 0 ? (
              cart.map((pet: any) => {
                return (
                  <article className="w-96 h-full border-2 rounded-lg shadow-xl mb-4" key={pet.pet_id}>
                    <div className="w-full h-2/6 border-b-2">
                      <img
                        className="w-full h-full object-cover"
                        src={pet.image}
                        alt={pet.name}
                      />
                    </div>

                    <div className="flex flex-col h-3/6 justify-evenly p-4 tracking-wide overflow-y-auto overflow-x-hidden break-words">
                      <div className="flex flex-row mb-2">
                        <p className="font-bold mr-1">Pet ID:</p> {pet.pet_id}
                      </div>
                      <div className="flex flex-row mb-2">
                        <p className="text-2xl italic underline font-bold mr-1">
                          {pet.name}
                        </p>
                      </div>
                      <div className="flex flex-row mb-2">
                        <p className="font-bold mr-1">Type: </p> {pet.type}
                      </div>
                      <div className="flex flex-row mb-2">
                        <p className="font-bold mr-1">Breed: </p> {pet.breed}
                      </div>
                      <div className="flex flex-row mb-2">
                        <p className="font-bold mr-1">Gender: </p> {pet.gender}
                      </div>
                      <div className="flex flex-row mb-2">
                        <p className="font-bold mr-1">Age: </p> {pet.age_month}{" "}
                        month
                      </div>
                      <p>{pet.description}</p>
                    </div>

                    <div className="flex flex-row h-1/6 justify-between items-center space-x-4 p-4 border-t-2">
                      <button
                        className="bg-blue-500 text-white px-4 py-2 rounded-lg transition ease-in-out hover:scale-110 hover:bg-indigo-500 duration-300"
                        onClick={() => {
                          setTogglePetConditions({
                            toggle: true,
                            data: {
                              ...pet,
                              condition_info: pet.condition_info || {}, // Fallback for condition_info
                            },
                          });
                        }}
                      >
                        View Pet Conditions
                      </button>
                      <button
                        className="bg-blue-500 text-white px-4 py-2 rounded-lg transition ease-in-out hover:scale-110 hover:bg-indigo-500 duration-300"
                        onClick={() => {
                          removeFromCart(pet.pet_id);
                        }}
                      >
                        Remove From Cart
                      </button>
                    </div>
                  </article>
                );
              })
            ) : (
              <div className="w-full h-full text-center text-xl font-bold">
                No Pets In Cart
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
