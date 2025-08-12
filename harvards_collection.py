import requests
import pymysql as sql
import streamlit as st
import pandas as pd

connection = sql.connect(
    host="localhost",
    user="root",
    password="343450",
    database="Project"
)

cursor = connection.cursor()

api_key = "cb953ab3-eb4b-4811-a8e5-79448736a698"
url = "https://api.harvardartmuseums.org/classification"

params = {
    "apikey":api_key,
    "size":100
}
response = requests.get(url, params)

data = response.json()

name = []

for i in data['records']:
    if i.get('objectcount', 1) >= 2500:
        name.append(i.get('name'))   

url = "https://api.harvardartmuseums.org/object"

def create_tables():
    cursor.execute(""" CREATE TABLE IF NOT EXISTS artifact_metadata(
                id INTEGER PRIMARY KEY,
                title TEXT,
                culture TEXT,
                period TEXT,
                century TEXT,
                medium TEXT,
                dimensions TEXT,
                description TEXT,
                department TEXT,
                classification TEXT,
                accessionyear INTEGER,
                accessionmethod TEXT);
                """)

    cursor.execute(""" CREATE TABLE IF NOT EXISTS artifact_media(
                objectid INT,
                imagecount INT,
                mediacount INTEGER,
                colorcount INTEGER,
                `rank` INTEGER,
                datebegin INT,
                dateend INT, 
                FOREIGN KEY(objectid) REFERENCES artifact_metadata(id));
                """)

    cursor.execute(""" CREATE TABLE IF NOT EXISTS artifact_colors(
                objectid INTEGER,
                color TEXT,
                spectrum TEXT,
                hue TEXT,
                percent REAL,
                css3 TEXT,
                FOREIGN KEY(objectid) REFERENCES artifact_metadata(id));
                """)
    connection.commit()

create_tables()

def get_classification(api_key, classification_input):
    all_records = []

    for page in range(1, 26):
        params = {
            "apikey":api_key,
            "size":100,
            "page":page,
            "classification":classification_input
        }

        response = requests.get(url, params=params)
        data = response.json()
        all_records.extend(data['records'])

        return all_records
    
def details(all_records):
    metadata = []
    media = []
    colors = []
    
    for i in all_records:
        metadata.append(dict(id = i['id'],
                             title = i['title'],
                             culture = i['culture'],
                             period = i['period'],
                             century = i['century'],
                             medium = i['medium'],
                             dimensions = i['dimensions'],
                             description = i['description'],
                             department = i['department'],
                             classification = i['classification'],
                             accessionyear = i['accessionyear'],
                             accessionmethod = i['accessionmethod']))
        
        media.append(dict(objectid = i['objectid'],
                           imagecount = i['imagecount'],
                           mediacount = i['mediacount'],
                           colorcount = i['colorcount'],
                           rank = i['rank'],
                           datebegin = i['datebegin'],
                           dateend = i['dateend']))
        
        sub_list = all_records[0]['colors']
        for j in sub_list:
            colors.append(dict(objectid = i['objectid'],
                                color = j['color'],
                                spectrum = j['spectrum'],
                                hue = j['hue'],
                                percent = j['percent'],
                                css3 = j['css3'])) 

    return metadata,media,colors

def insert_data(metadata, media, colors):
    query1 = """INSERT INTO artifact_metadata(id,title,culture,period,century,medium,dimensions,description,department,classification,accessionyear,accessionmethod) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
    query2 = """INSERT INTO artifact_media(objectid,imagecount,mediacount,colorcount,`rank`,datebegin,dateend) VALUES (%s,%s,%s,%s,%s,%s,%s)"""
    query3 = """INSERT INTO artifact_colors(objectid,color,spectrum,hue,percent,css3) VALUES (%s,%s,%s,%s,%s,%s)"""

    try:
        
        value1 = [(i.get('id'),i.get('title'),i.get('culture'),i.get('period'),i.get('century'),i.get('medium'),i.get('dimensions'),i.get('description'),i.get('department'),i.get('classification'),i.get('accessionyear'),
                        i.get('accessionmethod')) for i in metadata]
        cursor.executemany(query1, value1)

        
        value2 = [(i.get('objectid'),i.get('imagecount'),i.get('mediacount'),i.get('colorcount'),i.get('rank'),i.get('datebegin'),i.get('dateend')) for i in media]
        cursor.executemany(query2, value2)

        value3 = [(i.get('objectid'),i.get('color'),i.get('spectrum'),i.get('hue'),i.get('percent'),i.get('css3')) for i in colors]
        cursor.executemany(query3, value3)

        connection.commit()
        st.success("Inserted successfully")

    except Exception as e:
        st.error(f"Error inserting data: {e}")



st.set_page_config(layout="centered")

st.title("🏛️ Harvard's Artifacts Collection")

input = st.text_input("Enter a Classification:")

btn = st.button("Collect data")

choice = st.radio("Choices",["Select your choice","Migrate to SQL","SQL Queries"],horizontal=True)


if btn and input:
    result = get_classification(api_key, input)
    metadata,media,colors = details(result)

    st.session_state.metadata = metadata
    st.session_state.media = media
    st.session_state.colors = colors

    col1,col2,col3 = st.columns(3)
    with col1:
        st.header("Metadata")
        st.json(metadata)
    with col2:
        st.header("Media")
        st.json(media)
    with col3:
        st.header("Colors")
        st.json(colors)



if choice == "Migrate to SQL":
    btn1 = st.button("Insert")
    if btn1:
        if "metadata" in st.session_state:
            insert_data(st.session_state.metadata,st.session_state.media,st.session_state.colors)
            cursor.execute("SELECT * FROM artifact_metadata")
            rows = cursor.fetchall()
            df = pd.DataFrame(rows)
            st.dataframe(df)

elif choice == "SQL Queries":
    query_dict = {
        "1. List all artifacts from the 11th century belonging to Byzantine culture":
            "SELECT * FROM artifact_metadata WHERE culture = 'Byzantine' AND century = '11th century';",
        "2. What are the unique cultures represented in the artifacts?":
            "SELECT DISTINCT culture FROM artifact_metadata WHERE culture IS NOT NULL;",
        "3. List all artifacts from the Archaic Period":
            "SELECT * FROM artifact_metadata WHERE period = 'Archaic Period';",
        "4. List artifact titles ordered by accession year in descending order":
            "SELECT title, accessionyear FROM artifact_metadata ORDER BY accessionyear DESC;",
        "5. How many artifacts are there per department?":
            "SELECT department, COUNT(*) AS total FROM artifact_metadata GROUP BY department;",
        "6. Which artifacts have more than 3 images?":
            "SELECT am.id, am.title, am.classification, amedium.imagecount FROM artifact_metadata am JOIN artifact_media amedium ON am.id = amedium.objectid "
            "WHERE amedium.imagecount > 3;",
        "7. What is the average rank of all artifacts?":"SELECT AVG(`rank`) AS average_rank FROM artifact_media;",
        "8. Which artifacts have a higher mediacount than colorcount?":"SELECT am.id, am.title, amedium.mediacount, amedium.colorcount "
        "FROM artifact_metadata am JOIN artifact_media amedium ON am.id = amedium.objectid WHERE amedium.mediacount > amedium.colorcount;",
        "9. List all artifacts created between 1500 and 1600.":"SELECT am.id, am.title, amedium.datebegin, amedium.dateend "
        "FROM artifact_metadata am JOIN artifact_media amedium ON am.id = amedium.objectid WHERE amedium.datebegin >= 1500 AND amedium.dateend <= 1600;",
        "10. How many artifacts have no media files?":"SELECT COUNT(*) AS no_media_count FROM artifact_media WHERE mediacount = 0;",
        "11. What are all the distinct hues used in the dataset?":"SELECT DISTINCT hue FROM artifact_colors;",
        "12. What are the top 5 most used colors by frequency?":"SELECT hue, COUNT(*) AS frequency FROM artifact_colors "
        "GROUP BY hue ORDER BY frequency DESC LIMIT 5;",
        "13. What is the average coverage percentage for each hue?":"SELECT hue, AVG(percent) AS avg_coverage FROM artifact_colors GROUP BY hue;",
        "14.  List all colors used for a given artifact ID.":"SELECT hue, color, percent FROM artifact_colors WHERE objectid = 1234;",
        "15. What is the total number of color entries in the dataset?":"SELECT COUNT(*) AS total_color_entries FROM artifact_colors;",
        "16. List artifact titles and hues for all artifacts belonging to the Byzantine culture.":"SELECT am.title, ac.hue FROM artifact_metadata am "
        "JOIN artifact_colors ac ON am.id = ac.objectid WHERE am.culture = 'Byzantine';",
        "17. List each artifact title with its associated hues.":"SELECT am.title, GROUP_CONCAT(DISTINCT ac.hue ORDER BY ac.hue SEPARATOR ', ') AS hues "
        "FROM artifact_metadata am JOIN artifact_colors ac ON am.id = ac.objectid GROUP BY am.id, am.title;",
        "18. Get artifact titles, cultures, and media ranks where the period is not null.":"SELECT am.title, am.culture, amedia.rank FROM artifact_metadata am "
        "JOIN artifact_media amedia ON am.id = amedia.objectid WHERE am.period IS NOT NULL;",
        "19. Find artifact titles ranked in the top 10 that include the color hue 'Grey'.":"SELECT DISTINCT am.title FROM artifact_metadata am "
        "JOIN artifact_media amedia ON am.id = amedia.objectid JOIN artifact_colors ac ON am.id = ac.objectid WHERE amedia.rank <= 10 AND ac.hue = 'Grey';",
        "20. How many artifacts exist per classification, and what is the average media count for each?":"SELECT am.classification, COUNT(*) AS artifact_count, AVG(amedia.mediacount) AS avg_media_count "
        "FROM artifact_metadata am JOIN artifact_media amedia ON am.id = amedia.objectid GROUP BY am.classification;"
    }

    selected_description = st.selectbox(
    "Select a query",
    list(query_dict.keys()),
    index=None,
    placeholder="Select a query")

    if selected_description:
        sql_query = query_dict[selected_description]
        st.write(f"**Executing:** {sql_query}")

        cursor.execute(sql_query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        if rows:
            df = pd.DataFrame(rows, columns=columns)
            st.dataframe(df)
        else:
            st.info("No results found for this query.")