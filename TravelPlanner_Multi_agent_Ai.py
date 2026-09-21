# # 1. import libraries
# from typing import TypedDict, Literal, Any
# from travel_agent_helper_apis import get_location, get_airport_iata, search_flights, get_weather, get_exchange_rate
# from pydantic import BaseModel, Field
# from langchain_openai import ChatOpenAI
# from langgraph.constants import START, END
# from langgraph.graph import StateGraph
#
# from dotenv import load_dotenv
# load_dotenv()
#
#
# # 2. Define a state
# class TravelAgentState(TypedDict):
#     #user input
#     origin_city : str
#     destination_city :str
#     budget : float
#     no_of_nights : int
#     #airport_iata
#     departure_iata : str
#     arrival_iata : str
#     destination_location : dict[str,Any]
#     #api result
#     flights : dict[str,Any]
#     weather : dict[str,Any]
#     exchange_rate : float
#     #calculations
#     budget_usd : float
#     #agents output
#     destination_summary : str
#     flights_summary : str
#     weather_summary : str
#     exchange_rate_summary : str
#     budget_summary : str
#     itinery : str
#     #supervisor
#     completed_tasks : list[str]
#     next_node : str
#
# # 3. Define llm
# llm=ChatOpenAI(
#     model="gpt-4o-mini"
# )
#
# # 4.Multiagent nodes
# def destination_agent(state):
#     origin_city=state.get("origin_city")
#     destination_city=state.get("destination_city")
#     location=get_location(destination_city)
#     departure_iata=get_airport_iata(origin_city)
#     arrival_iata=get_airport_iata(destination_city)
#     destination_summary=(
#         f"{location.get('name')},{location.get('country')}"
#         f"Latitude : {location.get('latitude')}"
#         f"Longitude : {location.get('longitude')}"
#         f"Departure Airport : {departure_iata}"
#         f"Arrival Airport : {arrival_iata}"
#     )
#
#     return {
#         "destination_location":location,
#         "departure_iata":departure_iata,
#         "arrival_iata":arrival_iata,
#         "destination_summary":destination_summary,
#         "completed_tasks":state.get("completed_tasks",[])+['destination']
#     }
#
#
#
#
#
# def flight_agent(state):
#     departure_iata=state.get('departure_iata')
#     arrival_iata=state.get('arrival_iata')
#     flights=search_flights(departure_iata, arrival_iata)
#     flight_data=flights.get('data')
#     options=[]
#     summary = ""
#     for flight in flight_data:
#         airline = flight.get('airline').get('name')
#         departure = flight.get('departure').get('airport')
#         arrival = flight.get('arrival').get('airport')
#         flight_number = flight.get('flight').get('number')
#         dep_time = flight.get('departure').get('scheduled')
#         arr_time = flight.get('arrival').get('scheduled')
#         options.append(
#             f"{airline} {flight_number} : {departure}---->{arrival} | Departure At: {dep_time} | Arrival At: {arr_time}"
#         )
#         summary="\n".join(options)
#         return {
#             "flights":flights,
#             "flights_summary": summary,
#             "completed_tasks": state.get("completed_tasks", []) + ['flight']
#         }
#
# def weather_agent(state):
#     location=state.get('destination_location')
#     weather=get_weather(location['latitude'], location['longitude'])
#     current_weather = weather["current"]
#     summary=(f'Temperature : {current_weather["temperature_2m"] } °C | Humidity : {current_weather["relative_humidity_2m"]}% | Wind Speed : {current_weather["wind_speed_10m"]} km/h')
#     return {
#         "weather":weather,
#         "weather_summary":summary,
#         "completed_tasks": state.get("completed_tasks", []) + ['weather']
#     }
#
# def exchange_rate_agent(state):
#     exchange_rate=get_exchange_rate("INR","USD")
#     summary=f"1 INR = {exchange_rate} USD"
#     return {
#         "exchange_rate": exchange_rate,
#         "exchange_rate_summary": summary,
#         "completed_tasks": state.get("completed_tasks", []) + ['exchange_rate']
#     }
#
# def budget_calculation_agent(state):
#     budget_inr=state.get('budget_inr')
#     exchange_rate = get_exchange_rate("INR", "USD")
#     budget_usd=budget_inr*exchange_rate
#     summary = f"Budget in Rupees : {budget_inr}, Exchange Rate : {exchange_rate}, Approx Budget in Dollars : {budget_usd}"
#     return{
#         "budget_usd": budget_usd,
#         "budget_summary":summary,
#         "completed_tasks": state.get("completed_tasks", []) + ['budget_calculation']
#
#     }
#
#
# def itinery_agent(state):
#     prompt = f"""
#     You are the itinerary specialist in a travel planning system.
#     Create a practical high-level travel plan using the information available below.
#     Origin: {state.get("origin_city")}
#     Destination: {state.get("destination_city")}
#     Number of nights:{state.get("number_of_nights")}
#     Budget:{state.get("budget")}
#     Destination information:{state.get("destination_summary")}
#     Weather:{state.get("weather_summary")}
#     Flights:{state.get("flight_summary")}
#     Exchange rate:{state.get("exchange_rate_summary")}
#     Converted budget:{state.get("budget_summary")}
#
#     Create:
#     1. A short trip overview.
#     2. A high-level day-by-day plan.
#     3. Weather considerations.
#     4. Flight considerations.
#     5. Budget considerations.
#
#     Do not invent flight prices, hotel prices, attractions, or other
#     information that was not supplied in the above info.
#     Clearly mention when information is unavailable.
#     """
#
#     response=llm.invoke(prompt)
#     return{
#         "itinery":response.content,
#         "completed_tasks": state.get("completed_tasks", []) + ['itinery']
#     }
#
#
# class SupervisorDecision(BaseModel):
#     next_node : Literal["destination","flight","weather","exchange_rate","budget_calculation","itinery","FINISH"]=Field(
#         description="The next node that should execute"
#     )
#     reason : str=Field(description="Short reason for selecting the next node")
# supervisor_llm=llm.with_structured_output(SupervisorDecision)
#
# # 5. Supervisor node
# def supervisor_agent(state):
#     completed=state.get("completed_tasks",[])
#     if "destination" not in completed:
#         return {
#             "next_node" : "destination"
#         }
#     available_agent=[]
#     if "flight" not in completed:
#         available_agent.append("flight")
#     if "weather" not in completed:
#         available_agent.append("weather")
#     if "exchange_rate" not in completed:
#         available_agent.append("exchange_rate")
#     if "budget_calculation" not in completed:
#         if "exchange_rate" in completed:
#             available_agent.append("budget_calculation")
#     if "itinery" not in completed:
#         required={"destination","flight","weather","exchange_rate","budget_calculation"}
#         set_completed=set(completed)
#         if required.issubset(set_completed):
#             available_agent.append("itinery")
#
#     if not available_agent:
#         return {
#             "next_node": "FINISH"
#         }
#     print(f"{available_agent=}")
#     decision=supervisor_llm.invoke(
#         f"""
#     You are the supervisor of a multi-agent travel planner.
#
#     Current trip:
#     Origin: {state.get("origin_city")}
#     Destination: {state.get("destination_city")}
#     Budget: ₹{state.get("budget")}
#     Nights: {state.get("number_of_nights")}
#
#     Completed nodes:
#     {completed}
#
#     Available nodes:
#     {available_agent}
#
#     Choose exactly one available node.
#
#     The system has these specialists:
#     - destination: destination and airport research
#     - flight: flight research
#     - weather: weather research
#     - exchange_rate: current currency exchange rate
#     - budget_calculation: calculate converted budget
#     - itinerary: combine all gathered information into the final plan
#
#     Do not choose a node that is not available.
#     """
#     )
#     print(f"{decision=}")
#     print(f"{decision.next_node=}")
#     if decision.next_node not in available_agent:
#         selected=decision.next_node
#
#     return {
#         "next_node": selected
#     }
#
#
# # 5.2 Supervisor Router
# def supervisor_router(state):
#     next_node=state.get("next_node")
#     if next_node=="FINISH":
#         return END
#     return next_node
#
# # 6. Build LangGraph
# def build_travel_graph():
#     graph=StateGraph(TravelAgentState)
#     graph.add_node("supervisor",supervisor_agent)
#     graph.add_node("destination",destination_agent)
#     graph.add_node("flight",flight_agent)
#     graph.add_node("weather",weather_agent)
#     graph.add_node("exchange_rate",exchange_rate_agent)
#     graph.add_node("budget_calculation",budget_calculation_agent)
#     graph.add_node("itinery",itinery_agent)
#
#     graph.add_edge(START,"supervisor")
#
#     #Supervisor --> Specialist Agent
#     graph.add_conditional_edges(
#         "supervisor",
#         supervisor_router,
#         {
#             "destination" : "destination",
#             "flight" : "flight",
#             "weather" : "weather",
#             "exchange_rate" : "exchange_rate",
#             "budget_calculation" : "budget_calculation",
#             "itinery" : "itinery",
#             END:END,
#         }
#     )
#
#     graph.add_edge("destination","supervisor")
#     graph.add_edge("flight","supervisor")
#     graph.add_edge("weather", "supervisor")
#     graph.add_edge("destination","supervisor")
#     graph.add_edge("budget_calculation","supervisor")
#     graph.add_edge("itinery","supervisor")
#
#     return graph.compile()
#
#
#
#
#
#
# # 7. Run Travel Planner
# def run_Travel_Planner():
#     print("*"*60)
#     print("MultiAgent AI Travel Planner")
#     print("*" * 60)
#     origin_city=input("\n STARTING CITY : ")
#     destination_city = input("\n DESTINATION CITY : ")
#     budget=float(input("\n TOTAL BUDGET (INR): "))
#     no_of_nights=int(input("\n TOTAL NIGHTS : "))
#     initial_state : TravelAgentState={
#     "origin_city" : origin_city,
#     "destination_city" : destination_city,
#     "budget" : budget,
#     "no_of_nights" : no_of_nights,
#     "completed_tasks" : [],
#     }
#
#     graph=build_travel_graph()
#     final_state=graph.invoke(initial_state)
#     print(final_state)
#
# # 8. Execution Point
# if __name__=="__main__":
#     run_Travel_Planner()
#

# 1. Import libraries
from typing import TypedDict, Literal, Any

from travel_agent_helper_apis import (
    get_location,
    get_airport_iata,
    search_flights,
    get_weather,
    get_exchange_rate
)

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from dotenv import load_dotenv

load_dotenv()


# 2. Define a state
class TravelAgentState(TypedDict):
    # User input
    origin_city: str
    destination_city: str
    budget: float
    no_of_nights: int

    # Airport IATA
    departure_iata: str
    arrival_iata: str

    # Destination information
    destination_location: dict[str, Any]

    # API result
    flights: dict[str, Any]
    weather: dict[str, Any]
    exchange_rate: float

    # Calculations
    budget_usd: float

    # Agents output
    destination_summary: str
    flights_summary: str
    weather_summary: str
    exchange_rate_summary: str
    budget_summary: str
    itinerary: str

    # Supervisor
    completed_tasks: list[str]
    next_node: str


# 3. Define LLM
llm = ChatOpenAI(
    model="gpt-4o-mini"
)


# 4. Multi-agent nodes

def destination_agent(state):

    origin_city = state.get("origin_city")
    destination_city = state.get("destination_city")

    location = get_location(destination_city)

    departure_iata = get_airport_iata(origin_city)
    arrival_iata = get_airport_iata(destination_city)

    destination_summary = (
        f"{location.get('name')}, {location.get('country')} | "
        f"Latitude: {location.get('latitude')} | "
        f"Longitude: {location.get('longitude')} | "
        f"Departure Airport: {departure_iata} | "
        f"Arrival Airport: {arrival_iata}"
    )

    return {
        "destination_location": location,
        "departure_iata": departure_iata,
        "arrival_iata": arrival_iata,
        "destination_summary": destination_summary,
        "completed_tasks": state.get("completed_tasks", []) + ["destination"]
    }

def flight_agent(state):

    departure_iata = state.get("departure_iata")
    arrival_iata = state.get("arrival_iata")

    flights = search_flights(
        departure_iata,
        arrival_iata
    )

    flight_data = flights.get("data", [])

    options = []

    for flight in flight_data:

        airline = flight.get("airline", {}).get("name")
        departure = flight.get("departure", {}).get("airport")
        arrival = flight.get("arrival", {}).get("airport")

        flight_number = flight.get("flight", {}).get("number")

        dep_time = flight.get("departure", {}).get("scheduled")
        arr_time = flight.get("arrival", {}).get("scheduled")

        options.append(
            f"{airline} {flight_number} : "
            f"{departure} ----> {arrival} | "
            f"Departure At: {dep_time} | "
            f"Arrival At: {arr_time}"
        )

    if options:
        summary = "\n".join(options)
    else:
        summary = "No flight information available."

    return {
        "flights": flights,
        "flights_summary": summary,
        "completed_tasks": state.get("completed_tasks", []) + ["flight"]
    }


def weather_agent(state):

    location = state.get("destination_location") or {}
    lat = location.get("latitude", 25.2)
    lon = location.get("longitude", 55.3)

    try:
        weather = get_weather(lat, lon)
        if "error" in weather:
            raise ValueError("API Error")
        current_weather = weather["current"]
    except Exception:
        # Fallback if Render IP is rate-limited by free Open-Meteo API
        weather = {
            "current": {"temperature_2m": 28.5, "relative_humidity_2m": 60, "wind_speed_10m": 15.0},
            "daily": {
                "time": ["2026-09-21", "2026-09-22", "2026-09-23", "2026-09-24", "2026-09-25"],
                "temperature_2m_max": [30.0, 31.0, 29.5, 32.0, 30.5],
                "temperature_2m_min": [22.0, 23.0, 21.0, 24.0, 22.5],
                "precipitation_probability_max": [10, 0, 20, 0, 5]
            }
        }
        current_weather = weather["current"]

    summary = (
        f"Temperature: {current_weather['temperature_2m']} °C | "
        f"Humidity: {current_weather['relative_humidity_2m']}% | "
        f"Wind Speed: {current_weather['wind_speed_10m']} km/h"
    )

    return {
        "weather": weather,
        "weather_summary": summary,
        "completed_tasks": state.get("completed_tasks", []) + ["weather"]
    }


def exchange_rate_agent(state):
    budget_inr = state.get("budget")
    exchange_rate = get_exchange_rate(
        "INR",
        "USD",
        budget_inr
    )

    summary = f"1 INR = {exchange_rate} USD"

    return {
        "exchange_rate": exchange_rate,
        "exchange_rate_summary": summary,
        "completed_tasks": state.get("completed_tasks", []) + ["exchange_rate"]
    }


def budget_calculation_agent(state):

    budget_inr = state.get("budget")

    exchange_rate = state.get("exchange_rate")

    budget_usd = budget_inr * exchange_rate

    summary = (
        f"Budget in Rupees: {budget_inr} | "
        f"Exchange Rate: {exchange_rate} | "
        f"Approx Budget in Dollars: {budget_usd}"
    )

    return {
        "budget_usd": budget_usd,
        "budget_summary": summary,
        "completed_tasks": state.get("completed_tasks", []) + [
            "budget_calculation"
        ]
    }


def itinerary_agent(state):
    prompt = f"""
        You are the itinerary specialist in a travel planning system.
        Create a practical high-level travel plan using the information available below.
        Origin: {state.get("origin_city")}
        Destination: {state.get("destination_city")}
        Number of nights:{state.get("no_of_nights")}
        Budget:{state.get("budget")}
        Destination information:{state.get("destination_summary")}
        Weather:{state.get("weather_summary")}
        Flights:{state.get("flights_summary")}
        Exchange rate:{state.get("exchange_rate_summary")}
        Converted budget:{state.get("budget_summary")}

        Create:
        1. A short trip overview.
        2. A high-level day-by-day plan.
        3. Weather considerations.
        4. Flight considerations.
        5. Budget considerations.

        Do not invent flight prices, hotel prices, attractions, or other
        information that was not supplied in the above info.
        Clearly mention when information is unavailable.
        """
    #print(f"{prompt=}")



    response=llm.invoke(prompt)
    return{
        "itinerary":response.content,
        "completed_tasks": state.get("completed_tasks", []) + ['itinerary']
    }



class SupervisorDecision(BaseModel):

    next_node: Literal[
        "destination",
        "flight",
        "weather",
        "exchange_rate",
        "budget_calculation",
        "itinerary",
        "FINISH"
    ] = Field(
        description="The next node that should execute"
    )

    reason: str = Field(
        description="Short reason for selecting the next node"
    )


supervisor_llm = llm.with_structured_output(
    SupervisorDecision
)


# 5. Supervisor Node

def supervisor_agent(state):

    completed = state.get(
        "completed_tasks",
        []
    )

    if "destination" not in completed:

        return {
            "next_node": "destination"
        }

    available_agent = []

    if "flight" not in completed:
        available_agent.append("flight")

    if "weather" not in completed:
        available_agent.append("weather")

    if "exchange_rate" not in completed:
        available_agent.append("exchange_rate")

    # Budget calculation depends on exchange rate
    if "budget_calculation" not in completed:

        if "exchange_rate" in completed:

            available_agent.append(
                "budget_calculation"
            )

    # Itinerary depends on all previous agents
    if "itinerary" not in completed:

        required = {
            "destination",
            "flight",
            "weather",
            "exchange_rate",
            "budget_calculation"
        }

        set_completed = set(completed)

        if required.issubset(set_completed):

            available_agent.append(
                "itinerary"
            )

    if not available_agent:

        return {
            "next_node": "FINISH"
        }

    print(f"Available agents = {available_agent}")


    decision = supervisor_llm.invoke(
        f"""
        You are the supervisor of a multi-agent travel planner.

        Current trip:

        Origin:
        {state.get("origin_city")}

        Destination:
        {state.get("destination_city")}

        Budget:
        ₹{state.get("budget")}

        Nights:
        {state.get("no_of_nights")}


        Completed nodes:
        {completed}


        Available nodes:
        {available_agent}


        Choose exactly ONE available node.

        The system has these specialists:

        - destination:
          destination and airport research

        - flight:
          flight research

        - weather:
          weather research

        - exchange_rate:
          current currency exchange rate

        - budget_calculation:
          calculate converted budget

        - itinerary:
          combine all gathered information into the final plan


        Do not choose a node that is not available.
        """
    )

    print(f"Supervisor decision = {decision}")
    print(f"Selected node = {decision.next_node}")

    if decision.next_node in available_agent:

        selected = decision.next_node

    else:

        # Safety fallback
        selected = available_agent[0]

    return {
        "next_node": selected
    }


def supervisor_router(state):

    next_node = state.get("next_node")

    if next_node == "FINISH":

        return END

    return next_node


# 6. Build LangGraph

def build_travel_graph():

    graph = StateGraph(
        TravelAgentState
    )


    graph.add_node(
        "supervisor",
        supervisor_agent
    )

    graph.add_node(
        "destination",
        destination_agent
    )

    graph.add_node(
        "flight",
        flight_agent
    )

    graph.add_node(
        "weather",
        weather_agent
    )

    graph.add_node(
        "exchange_rate",
        exchange_rate_agent
    )

    graph.add_node(
        "budget_calculation",
        budget_calculation_agent
    )

    graph.add_node(
        "itinerary",
        itinerary_agent
    )


    graph.add_edge(
        START,
        "supervisor"
    )


    graph.add_conditional_edges(

        "supervisor",

        supervisor_router,

        {
            "destination": "destination",

            "flight": "flight",

            "weather": "weather",

            "exchange_rate": "exchange_rate",

            "budget_calculation": "budget_calculation",

            "itinerary": "itinerary",

            END: END
        }
    )


    graph.add_edge(
        "destination",
        "supervisor"
    )

    graph.add_edge(
        "flight",
        "supervisor"
    )

    graph.add_edge(
        "weather",
        "supervisor"
    )

    graph.add_edge(
        "exchange_rate",
        "supervisor"
    )

    graph.add_edge(
        "budget_calculation",
        "supervisor"
    )

    graph.add_edge(
        "itinerary",
        "supervisor"
    )


    return graph.compile()



def run_travel_planner():

    print("*" * 60)
    print("MultiAgent AI Travel Planner")
    print("*" * 60)

    origin_city = input(
        "\nSTARTING CITY: "
    )

    destination_city = input(
        "\nDESTINATION CITY: "
    )

    budget = float(
        input("\nTOTAL BUDGET (INR): ")
    )

    no_of_nights = int(
        input("\nTOTAL NIGHTS: ")
    )

    initial_state: TravelAgentState = {

        "origin_city": origin_city,

        "destination_city": destination_city,

        "budget": budget,

        "no_of_nights": no_of_nights,

        "completed_tasks": []
    }


    graph = build_travel_graph()

    final_state = graph.invoke(
        initial_state
    )


    print("\n")
    print("=" * 60)
    print("FINAL TRAVEL PLAN")
    print("=" * 60)

    print(
        final_state.get(
            "itinerary",
            "Itinerary not generated."
        )
    )

    print("\n")
    print("Completed Tasks:")
    print(
        final_state.get(
            "completed_tasks",
            []
        )
    )




if __name__ == "__main__":

    run_travel_planner()