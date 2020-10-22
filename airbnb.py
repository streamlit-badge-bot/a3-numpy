import streamlit as st
import pandas as pd
import altair as alt
import pydeck as pdk
import numpy as np
import geopandas as gp
import plotly.express as px


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


st.title("Airbnb listings in San Francisco🏠")


st.markdown('In this project, we are going to analyze the airbnb listing data in San Francisco. ✈️')

st.markdown('Let\'s take a look at the raw data from [insideAirbnb](http://insideairbnb.com/) and its descriptive statstics.')

if st.checkbox("Show Raw Data"):
    st.dataframe(df_listing.head())

if st.checkbox('Show Data Statistics'):
	st.dataframe(df_listing.describe())

geodata = load_geojson_data()


st.header("Listing Locations")

df_nbh = df_listing.groupby('neighbourhood_cleansed').mean()

st.markdown('We are interested in the popular areas of SF, from the chart we could observe that *Seacliff* and *Maria* are with higher average price. If the trip is budgeted, we could look into other neighbourhoods like *Crocker Amazon*.')

bar = px.bar(df_nbh['price'].sort_values(ascending=False).reset_index(), x="neighbourhood_cleansed", y='price', title="Average price of each neighbourhood in SF", color = 'neighbourhood_cleansed')
bar.update_xaxes(title="Neighbourhood")
bar.update_yaxes(title="Price")
st.plotly_chart(bar)
#print(df_nbh)

stats_nbh = geodata.merge(df_nbh, left_on = 'neighbourhood', right_on = 'neighbourhood_cleansed')
print(stats_nbh['price'])

# midpoint = (np.average(df_listing['longitude']), np.average(df_listing['latitude']))

stats = geodata.merge(df_listing, 'left', 'neighbourhood')



room_types = list(df_listing['room_type'].unique())
neighbourhoods = [CITY] + list(df_listing['neighbourhood_cleansed'].unique())

st.markdown('Knowing the price distribution across the neighbourhoods, we are then going to explore more on data. The map visualization below gives a clearer insight of the listings in SF, the color indicates the room types and the size of circle indicates the price.\
	By interacting with the widget you could explore more factors that affect the prices, try it out🙌')
st.header("Map Visualization")
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

if st.checkbox("Show Filtered Data"):
    data_num = st.text_input("Number of data (Max 30)", 5)
    data_num = min(int(data_num),30)
    st.dataframe(df_listing.head(data_num))

midpoint = (np.average(filtered_listing['longitude']), np.average(filtered_listing['latitude']))

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
    		 get_radius='price / 5 + 30',          # Radius is given in meters
    		 get_fill_color='[color_r, color_g, color_b, color_a]',  # Set an RGBA value for fill
    		 pickable=True,
    		 )
     ],
     tooltip={
     		'html':tooltip_html,
     		},
 )


st.pydeck_chart(deck)

st.header("Availability")

st.write("Then let's look at the availability of the rooms in SF. Here we define it of *HIGH* availability if its available days >= 60 in a year.")

df_available = df_listing.groupby('availability').count().reset_index()
pie = px.pie(df_available, values=df_available['availability_365'], names= df_available['availability'], title="Pie Chart of Availability", color = df_available['availability'])

st.plotly_chart(pie)

st.write("An observation is that the room is either fully available or not available.")

his = px.histogram(df_listing, x="availability_365", nbins=100, title="Availability distribution")
his.update_xaxes(title="Availability Days")
his.update_yaxes(title="Listings")
st.plotly_chart(his)

st.header("Scatter Visualization of Price")


st.markdown('In addition, we want to learn how the number of bedrooms, ratings and capacity affect the price.')

column = ["neighbourhood_cleansed","bedrooms","beds","review_scores_rating", "accommodates"]
x_axis = st.selectbox('X Axis',column)

color_list = ["room_type", "neighbourhood_cleansed", "bedrooms", "review_scores_rating"]
scatter_color = st.selectbox('Color', color_list)

scatter = alt.Chart(filtered_listing).mark_point().encode(
    alt.X(x_axis),
    alt.Y("price"),
    alt.Color(scatter_color)
)

st.write(scatter)

st.header("Price Estimation")
st.markdown('Finally, before we actually book an order, let\'s estimate how much we are going to pay.')
st.write("Please provide the room type, location and the number of bedrooms")
est_list = ["room_type", "neighbourhood_cleansed", "bedrooms"]
est_room_type = st.selectbox('Room Type', df_listing['room_type'].unique())
est_neigh = st.selectbox('Location', df_listing['neighbourhood_cleansed'].unique())
est_bed = st.selectbox('Number of Bedroom', df_listing['bedrooms'].unique())

# kNN algorithm, take average for tie-break
est_listing = df_listing[
    df_listing['room_type'].isin([est_room_type]) &
    df_listing['bedrooms'].isin([est_bed]) &
    df_listing['neighbourhood_cleansed'].isin(neighbourhoods if est_neigh == CITY else [est_neigh])
    ]

est_price = int(est_listing["price"].mean())
if est_price==0:
    st.write("Fail to estimate the price.")
else:
    st.write("The estimation price is: $"+str(est_price)+" per night.")

# tooltipnbh_html = """
# <h3>{price}</h3>
# """

# deck_nbh = pdk.Deck(
# 	map_style='mapbox://styles/mapbox/light-v10',
# 	initial_view_state=pdk.ViewState(
# 		latitude=midpoint[1],
# 		longitude=midpoint[0],
# 		zoom=11.5,
# 		min_zoom=10,
# 		max_zoom=13,
# 		pitch=40.5,
# 		bearing=-27.36
#      ),
# 	layers=[
#          pdk.Layer(
#              'GeoJsonLayer',
#              data=stats_nbh,
#              get_position='[longitude, latitude]',
#              get_fill_color='[color_r, color_g, color_b, color_a]',
#              get_elevation='price',
#              elevation_scale = 20,
#              get_line_color=[0,0,0],
#              get_line_width=10,
#              opacity=1.0,
#              stroked=False,
#              filled=True,
#              extruded=True,
#              pickable=True,
#              #wireframe=True,
#          ),
#     ],
#     tooltip=tooltipnbh_html,
# )
# st.pydeck_chart(deck_nbh)