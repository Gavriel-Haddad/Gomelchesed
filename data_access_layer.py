import streamlit as st
import sqlalchemy as sa
import pandas as pd

engine = sa.create_engine(r"postgresql://Gomelchesed_owner:npg_Bz0SUtTPgkv1@ep-spring-river-a20x0ye0-pooler.eu-central-1.aws.neon.tech/Gomelchesed?sslmode=require")

st.write(pd.read_sql("people", engine.connect()))
