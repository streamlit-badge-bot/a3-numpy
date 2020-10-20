import streamlit as st
import pandas as pd
import altair as alt
import pydeck as pdk
import numpy as np
import geopandas as gp


CITY = "San Francisco"

ROOM_TYPE_COLORS = {
    "Private room": "blue",
    "Entire home/apt": "green",
    "Shared room": "orange",
    "Hotel room": "red",
}

COLORS_R = {"green": 0, "blue": 0, "orange": 255, "gray": 128, "red": 165,}

COLORS_G = {"green": 128, "blue": 0, "orange": 165, "gray": 128, "red": 0,}

COLORS_B = {"green": 0, "blue": 255, "orange": 0, "gray": 128, "red": 0, }

st.title("Let's analyze some Airbnb listings Data🏠")

@st.cache
def load_data():
	listings_url = "data/listings.csv"
	review_url = "data/review.csv"

	listing, review = pd.read_csv(listings_url), pd.read_csv(review_url)
	listing['price'] = listing['price'].apply(lambda x : x[1:].replace(',', '')).astype(float)
	listing = listing[listing['price'].between(listing['price'].quantile(.01), listing['price'].quantile(.99))]
	listing = listing.fillna(0)

	listing["color"] = listing['room_type'].map(ROOM_TYPE_COLORS)
	listing["color"] = listing["color"].fillna("gray")
	listing["color_r"] = listing["color"].map(COLORS_R)
	listing["color_g"] = listing["color"].map(COLORS_G)
	listing["color_b"] = listing["color"].map(COLORS_B)
	listing["color_a"] = 140

	listing['availability'] = listing.apply(lambda x : 'High' if x['availability_365'] > 60 else 'Low', axis=1)
	return listing, review

@st.cache
def load_geojson_data():
	geodata_url = "data/neighbourhoods.geojson"
	return gp.read_file(geodata_url)

df_listing, df_review = load_data()


st.write("Let's look at raw data in the Pandas Data Frame.")

st.dataframe(df_listing.head())

geodata = load_geojson_data()


st.write("Here's the location of those listings.")

midpoint = (np.average(df_listing['longitude']), np.average(df_listing['latitude']))

stats = geodata.merge(df_listing, 'left', 'neighbourhood')

# Sidebar
room_types = list(df_listing['room_type'].unique())
neighbourhoods = [CITY] + list(df_listing['neighbourhood_cleansed'].unique())

room_types_multiselect = st.multiselect(
    label='Room types',
    options=room_types,
    default=room_types[:2]
)

neighbourhoods_selectbox = st.selectbox(
	'Neighbourhoods',
	neighbourhoods)

price_range = st.slider('Price Range', float(df_listing['price'].min()), float(df_listing['price'].max()), value=[50., 500.])


filtered_listing = df_listing[
    df_listing['room_type'].isin(room_types_multiselect) &
    df_listing['price'].between(price_range[0], price_range[1]) &
    df_listing['neighbourhood_cleansed'].isin(neighbourhoods if neighbourhoods_selectbox == CITY else [neighbourhoods_selectbox])
    ]

tooltip_html = """
    <a href="{listing_url}">
    <h3>{name}</h3>
    </a>
    <img src="{picture_url}" style="width:25%; height:25%;"/>
    <table>
        <tr>
            <th>Room type:</th>
            <td>{room_type}</td>
        </tr>
        <tr>
            <th>Price:</th>
            <td>${price}</td>
        </tr>
        <tr>
            <th>Neighbourhood:</th>
            <td>{neighbourhood_cleansed}</td>
        </tr>
        <tr>
            <th>Accomodates:</th>
            <td>{accommodates}</td>
        </tr>
        <tr>
            <th>Availability:</th>
            <td>{availability} ({availability_365}days/year)</td>
        </tr>
        <tr>
            <th>Reviews:</th>
            <td>{number_of_reviews}</td>
        </tr>
        <tr>
            <th>Last Review:</th>
            <td>{last_review}</td>
        </tr>
    </table>
"""

deck = pdk.Deck(
	map_style='mapbox://styles/mapbox/light-v10',
	initial_view_state=pdk.ViewState(
		latitude=midpoint[1],
		longitude=midpoint[0],
		zoom=11.5,
		min_zoom=10,
		max_zoom=13,
     ),
	layers=[
         pdk.Layer(
             'GeoJsonLayer',
             data=stats,
             get_position='[longitude, latitude]',
             get_line_color=[0,0,0],
             get_line_width=10,
             opacity=0.01
         ),
         pdk.Layer(
    		 'ScatterplotLayer',     # Change the `type` positional argument here
    		 data=filtered_listing,
    		 get_position='[longitude, latitude]',
    		 auto_highlight=True,
    		 get_radius=30,          # Radius is given in meters
    		 get_fill_color='[color_r, color_g, color_b, color_a]',  # Set an RGBA value for fill
    		 pickable=True,
    		 )
     ],
     tooltip={
     		'html':tooltip_html,
     		},
 )

st.pydeck_chart(deck)