"""Shared Phase 3 settings: column groups, valid ranges and encoding levels."""

from __future__ import annotations

COLUMN_RENAMES = {
    "Tourism_Revenue_USD": "Tourism_Revenue_USD_000",
    "Eco_Tourism_Revenue_USD": "Eco_Tourism_Revenue_USD_000",
}
TEXT_COLUMNS = ("Country", "City", "Purpose_of_Visit", "Hotel_Rating")
INTEGER_COLUMNS = (
    "Year", "Month", "Number_of_Tourists", "Number_of_Hotels", "Employment_in_Tourism",
    "Number_of_Flights", "Airport_Passenger_Traffic", "Number_of_Online_Reviews",
)
POSITIVE_COLUMNS = (
    "Number_of_Tourists", "Average_Length_of_Stay", "Tourist_Spending_USD", "Number_of_Hotels",
    "Average_Room_Price_USD", "Tourism_Revenue_USD", "Employment_in_Tourism",
    "Number_of_Flights", "Airport_Passenger_Traffic", "Eco_Tourism_Revenue_USD",
    "Carbon_Footprint_kg", "Number_of_Online_Reviews",
)
VALID_RANGES = {
    "Year": (2020, 2024),
    "Month": (1, 12),
    "Hotel_Occupancy_Rate": (0, 100),
    "Contribution_to_GDP_Percent": (0, 100),
    "Transport_Infrastructure_Quality": (1, 10),
    "Waste_Management_Rating": (1, 10),
    "Tourist_Satisfaction_Score": (1, 10),
}
HOTEL_STAR_LEVELS = {f"{n}-star": n for n in range(1, 6)}
HOTEL_RATING_LEVELS = ("Unrated", *HOTEL_STAR_LEVELS)
PURPOSE_LEVELS = (
    "Business", "Cultural", "Educational", "Family Visit", "Leisure", "Medical", "Religious",
)
REVENUE_IDENTITY_TOLERANCE = 0.011

# Names the UN M49 table spells differently from the Kaggle file (join-key standardisation).
COUNTRY_CROSSWALK = {
    "Turkey": "Türkiye",
    "United Kingdom": "United Kingdom of Great Britain and Northern Ireland",
    "United States": "United States of America",
}
SOUTHERN_HEMISPHERE_COUNTRIES = frozenset({"Australia", "Brazil", "South Africa"})

LARGEST_AIRLINER_SEATS = 853  # Airbus A380 maximum certified seating
PEOPLE_SHARING_A_ROOM = 2
DEMAND_TIER_LABELS = ("Low", "Medium-Low", "Medium-High", "High")
OCCUPANCY_BAND_LABELS = ("Low", "Moderate", "High", "Very High")
BIN_COUNT = 4
DERIVED_DECIMALS = 4
SCALED_DECIMALS = 6
REDUNDANCY_THRESHOLD = 0.7

OUTLIER_MEASURES = (
    "Number_of_Tourists", "Average_Length_of_Stay", "Tourist_Spending_USD",
    "Hotel_Occupancy_Rate", "Number_of_Hotels", "Average_Room_Price_USD",
    "Tourism_Revenue_USD_000", "Employment_in_Tourism", "Contribution_to_GDP_Percent",
    "Number_of_Flights", "Airport_Passenger_Traffic", "Transport_Infrastructure_Quality",
    "Eco_Tourism_Revenue_USD_000", "Carbon_Footprint_kg", "Waste_Management_Rating",
    "Tourist_Satisfaction_Score", "Number_of_Online_Reviews",
)
ENGINEERED_MEASURES = (
    "Spend_per_Night_USD", "Tourist_Nights", "Tourists_per_Hotel", "Eco_Revenue_Share_Pct",
    "Carbon_kg_per_Tourist", "Passengers_per_Flight",
)
SCALED_PREDICTORS = (
    "Year", "Average_Length_of_Stay", "Tourist_Spending_USD", "Hotel_Occupancy_Rate",
    "Number_of_Hotels", "Average_Room_Price_USD", "Employment_in_Tourism",
    "Contribution_to_GDP_Percent", "Number_of_Flights", "Airport_Passenger_Traffic",
    "Transport_Infrastructure_Quality", "Waste_Management_Rating",
    "Tourist_Satisfaction_Score", "Number_of_Online_Reviews",
)
ONE_HOT_SOURCES = {
    "Country": "Country", "Purpose_of_Visit": "Purpose",
    "Season": "Season", "Hotel_Rating": "Rating",
}
OUTLIER_FLAGS = {
    "Eco_Tourism_Revenue_USD_000": ("Outlier_Eco_Revenue_IQR", "Outlier_Eco_Revenue_3SD"),
    "Carbon_Footprint_kg": ("Outlier_Carbon_IQR", "Outlier_Carbon_3SD"),
}
TARGET_DERIVED_COLUMNS = frozenset({
    "Tourism_Revenue_USD_000", "Eco_Tourism_Revenue_USD_000", "Carbon_Footprint_kg",
    "Tourists_per_Hotel", "Tourist_Nights", "Carbon_kg_per_Tourist", "Eco_Revenue_Share_Pct",
    "Demand_Tier", "Demand_Tier_Code", "Flag_Passengers_Below_Tourists", *(
        flag for pair in OUTLIER_FLAGS.values() for flag in pair
    ),
})
