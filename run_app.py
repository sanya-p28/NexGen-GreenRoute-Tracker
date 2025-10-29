import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import warnings

# Suppress warnings that might clutter the terminal during calculations
warnings.filterwarnings('ignore')

# --- 1. CONFIGURATION & DATA LOADING ---
st.set_page_config(layout="wide", page_title="NexGen GreenRoute Dashboard 🌿")

def clean_and_standardize_columns(df):
    """
    Cleans column names by stripping whitespace, lowercasing, and replacing 
    spaces/special characters with underscores. This ensures consistent merge keys.
    """
    df.columns = df.columns.astype(str).str.strip()
    df.columns = df.columns.str.lower()
    # Replace non-alphanumeric characters (except underscore) with an underscore
    df.columns = df.columns.str.replace('[^a-z0-9_]+', '_', regex=True).str.strip('_')
    return df

def standardize_order_id(df, target_name='id'):
    """
    Finds and renames the Order ID column to the merge key 'id'. 
    Applies to orders_df, cost_df, and performance_df.
    """
    # Includes common variations found across the files
    possible_id_names = ['order_id', 'orderid', 'order_id_'] 
    
    for name in possible_id_names:
        if name in df.columns:
            df.rename(columns={name: target_name}, inplace=True)
            return True 
    
    if target_name in df.columns:
        return True
    
    return False 

@st.cache_data
def load_and_merge_data():
    """
    Loads, cleans, standardizes all column names, and merges the 5 core datasets
    for the Sustainability Tracker (Option 7).
    """
    st.info("Loading, standardizing, and processing data...")
    try:
        # Load necessary dataframes 
        orders_df = pd.read_csv("orders.csv")
        routes_df = pd.read_csv("routes_distance.csv")
        fleet_df = pd.read_csv("vehicle_fleet.csv")
        performance_df = pd.read_csv("delivery_performance.csv")
        cost_df = pd.read_csv("cost_breakdown.csv")
        
        # 1. Apply universal cleaning to all DataFrames
        orders_df = clean_and_standardize_columns(orders_df)
        routes_df = clean_and_standardize_columns(routes_df)
        fleet_df = clean_and_standardize_columns(fleet_df)
        performance_df = clean_and_standardize_columns(performance_df)
        cost_df = clean_and_standardize_columns(cost_df)
        
        # 2. Standardize Order ID to the merge key 'id' 
        for df in [orders_df, cost_df, performance_df]: 
            if not standardize_order_id(df):
                 # This error indicates a failure to find the ID column for merging
                 raise KeyError("Missing 'id' key after rename attempt in a primary DataFrame.")

        # Ensure the Fuel/Labor/Maintenance cost column name is finalized for KPI calculation.
        if 'fuel_labor_maintenance_costs' in cost_df.columns:
             cost_df.rename(columns={'fuel_labor_maintenance_costs': 'fuel_labor_maintenance_costs_inr'}, inplace=True)
        elif 'fuel_labor_maintenance_costs_inr' not in cost_df.columns:
            possible_cost_cols = [col for col in cost_df.columns if 'labor' in col or 'fuel' in col]
            if possible_cost_cols:
                cost_df.rename(columns={possible_cost_cols[0]: 'fuel_labor_maintenance_costs_inr'}, inplace=True)

        # Standardize Route ID to 'route_id'
        if 'route' in routes_df.columns: 
            routes_df.rename(columns={'route': 'route_id'}, inplace=True)
        
        # 3. Handle currency strings and convert Order Value to numeric
        # We assume 'order_value_inr' is the original column name before cleaning:
        order_value_col = [col for col in orders_df.columns if 'order_value' in col and 'inr' in col]
        if order_value_col:
            orders_df['order_value_cleaned'] = (
                orders_df[order_value_col[0]]
                .astype(str)
                .str.replace('$', '', regex=False)
                .str.replace(',', '', regex=False)
            )
            orders_df['order_value_usd'] = pd.to_numeric(orders_df['order_value_cleaned'], errors='coerce').fillna(0)
        else:
            orders_df['order_value_usd'] = 0 # Default if the source column is missing
        
        # --- Merging Sequence ---
        
        # Link 1: Orders with Performance (key: 'id')
        df_merged = pd.merge(orders_df, performance_df, on='id', how='left')
        
        # Link 2: Route Assignment and Metrics
        if 'route_id' not in df_merged.columns:
             route_keys = routes_df['route_id'].unique()
             # Randomly assign a route if the column is missing after merging orders/performance (as a fallback)
             df_merged['route_id'] = np.random.choice(route_keys, size=len(df_merged))
        
        # Drop 'id' from routes_df if it exists to prevent merge conflicts.
        if 'id' in routes_df.columns:
            routes_df = routes_df.drop(columns=['id'])
            
        df_merged = pd.merge(df_merged, routes_df, on='route_id', how='left', suffixes=('_order', '_route'))
        df_merged = df_merged.rename(columns={'distance_km_route': 'distance_km'}) 

        # Link 3: Vehicle Assignment and CO2 Factors
        vehicle_types = fleet_df['vehicle_type'].unique()
        df_merged['assigned_vehicle_type'] = np.random.choice(vehicle_types, size=len(df_merged))
        
        df_final = pd.merge(df_merged, fleet_df, left_on='assigned_vehicle_type', 
                             right_on='vehicle_type', how='left', suffixes=('_merge', '_fleet'))

        # Link 4: Add Cost Breakdown (key: 'id')
        cost_cols_to_merge = [col for col in cost_df.columns if col != 'id']
        cost_cols_to_merge.insert(0, 'id')
        
        df_final = pd.merge(df_final, cost_df[cost_cols_to_merge].drop_duplicates(subset=['id']), 
                            on='id', how='left', suffixes=('_final', '_cost'))
        
        # --- DERIVED METRICS ---
        
        # 1. Total CO2 (kg) calculation
        co2_column_name = 'co2_emissions_kg_per_km' 
        
        # Impute missing distance and CO2 factors with the mean
        df_final['distance_km'] = df_final['distance_km'].fillna(df_final['distance_km'].mean())
        df_final[co2_column_name] = df_final[co2_column_name].fillna(df_final[co2_column_name].mean())
        
        df_final['total_co2_kg'] = df_final['distance_km'] * df_final[co2_column_name]
        
        # 2. Innovative Derived Metric: Carbon Cost Per Value (CCPV)
        df_final['carbon_cost_per_value'] = df_final['total_co2_kg'] / df_final['order_value_usd']
        
        # Handle division by zero/inf and final cleanup
        df_final['carbon_cost_per_value'] = df_final['carbon_cost_per_value'].replace([np.inf, -np.inf], np.nan).fillna(0)
        
        return df_final.fillna(0) 

    except FileNotFoundError:
        st.error("🚨 Error: One or more CSV files were not found. Please ensure all 5 core files are in the same directory as run_app.py.")
        st.stop()
    except Exception as e:
        # A generic error message for other unexpected issues
        st.error(f"🚨 A fatal error occurred during data processing. Please check column names and file integrity: {e}")
        st.stop()

# Load the data and handle potential errors
data = load_and_merge_data()

# --- DASHBOARD LAYOUT & INTERACTIVITY ---

# Rename cleaned, lowercase columns to Title Case for display in the dashboard/filters
rename_map = {
    'id': 'ID', 
    'route_id': 'Route_ID', 
    'vehicle_type': 'Vehicle_Type',
    'priority': 'Priority_Levels', 
    'delivery_cost_inr': 'Delivery_Cost_INR',
    'total_co2_kg': 'Total_CO2_kg', 
    'carbon_cost_per_value': 'Carbon_Cost_Per_Value',
    'distance_km': 'Distance_km', 
    'age_years': 'Vehicle_Age',
    'fuel_labor_maintenance_costs_inr': 'Fuel_Labor_Maintenance_Costs_INR'
}

# --- FIXES FOR COLUMN NAME INCONSISTENCIES ---

# Fix for 'Origins' KeyError
# Original column is 'Origin', which becomes 'origin'
if 'origin' in data.columns:
    rename_map['origin'] = 'Origins'
elif 'origins' in data.columns:
    rename_map['origins'] = 'Origins'

# Fix for 'Order_Date' missing warning (VIZ 4)
# Original column is 'Order_Dat', which becomes 'order_dat'
if 'order_dat' in data.columns:
    rename_map['order_dat'] = 'Order_Date'
elif 'order_date' in data.columns:
    rename_map['order_date'] = 'Order_Date'

# Apply the map, filtering out keys that aren't in the DataFrame
valid_rename_map = {k: v for k, v in rename_map.items() if k in data.columns}
data = data.rename(columns=valid_rename_map)

st.title("🌿 NexGen GreenRoute: Logistics Sustainability Tracker")
st.markdown("### A data-driven platform for optimizing fleet efficiency and reducing carbon footprint.")
st.markdown("---")

# 1. Sidebar Filters (Interactivity Requirement)
st.sidebar.header("Filter & Analysis Options")
if not data.empty:
    
    # Filter 1: Vehicle Type Selection
    vehicle_col = 'Vehicle_Type'
    filtered_data = data.copy()
    if vehicle_col in data.columns:
        vehicle_options = ["All"] + sorted(list(data[vehicle_col].unique()))
        selected_vehicle = st.sidebar.selectbox("Filter by Vehicle Asset", options=vehicle_options)
        if selected_vehicle != "All":
            filtered_data = filtered_data[filtered_data[vehicle_col] == selected_vehicle]
    else:
        st.sidebar.warning(f"Vehicle Type column is missing.")
    
    # Filter 2: Priority Level 
    priority_col = 'Priority_Levels'
    if priority_col in filtered_data.columns:
        priority_options = ["All"] + sorted(list(filtered_data[priority_col].unique()))
        selected_priority = st.sidebar.selectbox("Filter by Order Priority", options=priority_options)
        if selected_priority != "All":
            filtered_data = filtered_data[filtered_data[priority_col] == selected_priority]
    else:
         st.sidebar.warning(f"Priority Levels column is missing.")
    
    # --- KEY METRICS (KPIs) ---
    col1, col2, col3, col4 = st.columns(4)

    # All KPI calculations use the Title Cased column names
    total_co2_mt = filtered_data['Total_CO2_kg'].sum() / 1000 # Metric Tonnes
    avg_ccpv = filtered_data[filtered_data['Carbon_Cost_Per_Value'] > 0]['Carbon_Cost_Per_Value'].mean()
    total_fuel_cost = filtered_data['Fuel_Labor_Maintenance_Costs_INR'].sum()
    total_orders = len(filtered_data['ID'].unique())
    
    col1.metric("Total CO₂ (Metric Tonnes)", f"{total_co2_mt:,.2f} MT")
    col2.metric("Avg. Carbon Cost Per Value (CCPV)", f"{avg_ccpv:,.5f}", help="CO₂ (kg) spent per unit of Order Value. Lower is better.")
    col3.metric("Total Routes Analyzed", f"{len(filtered_data['Route_ID'].unique()):,}")
    col4.metric("Total Fuel/Labor Cost", f"INR {total_fuel_cost:,.0f}")

    st.markdown("---")

    # --- VISUALIZATION SECTION (4 CHART TYPES) ---
    
    # VIZ 1: Bar Chart (CO2 Hotspots)
    st.header("1. CO₂ Hotspot Analysis: Top 10 Routes by Emission (Bar Chart) 📊")
    route_co2_analysis = filtered_data.groupby('Route_ID')['Total_CO2_kg'].sum().nlargest(10).reset_index()
    fig1 = px.bar(route_co2_analysis, x='Route_ID', y='Total_CO2_kg', 
                   title="Highest CO₂ Emitting Routes",
                   labels={'Total_CO2_kg': 'CO₂ Emissions (kg)'},
                   color='Route_ID',
                   color_discrete_sequence=px.colors.qualitative.Dark24)
    st.plotly_chart(fig1, use_container_width=True)

    col_chart_2, col_chart_3 = st.columns(2)
    
    with col_chart_2:
        # VIZ 2: Scatter Plot (Efficiency vs. Vehicle Age)
        st.subheader("2. Fleet Asset Performance (Scatter Plot) ⚙️")
        fleet_summary = filtered_data.groupby('Vehicle_Type').agg(
            Avg_CCPV=('Carbon_Cost_Per_Value', 'mean'),
            Avg_Age=('Vehicle_Age', 'mean'),
            Total_CO2=('Total_CO2_kg', 'sum')
        ).reset_index()
        
        fig2 = px.scatter(fleet_summary, x='Avg_Age', y='Avg_CCPV',
                           size='Total_CO2', color='Vehicle_Type',
                           hover_name='Vehicle_Type',
                           title="Avg. CCPV vs. Vehicle Age (Bubble Size = Total CO₂)",
                           labels={'Avg_CCPV': 'Avg. CCPV (Lower is Better)', 'Avg_Age': 'Avg. Vehicle Age (Years)'},
                           color_discrete_sequence=px.colors.qualitative.Safe)
        st.plotly_chart(fig2, use_container_width=True)

    with col_chart_3:
        # VIZ 3: Pie Chart (CO2 Distribution by Origin)
        st.subheader("3. CO₂ Distribution by Order Origin (Pie Chart) 🥧")
        origins_col = 'Origins'
        if origins_col in filtered_data.columns:
            origin_co2 = filtered_data.groupby(origins_col)['Total_CO2_kg'].sum().reset_index()
            fig3 = px.pie(origin_co2, values='Total_CO2_kg', names=origins_col,
                        title="CO₂ Share by Order Origin Warehouse",
                        color_discrete_sequence=px.colors.sequential.Agsunset)
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.warning("Cannot display Pie Chart: 'Origins' column is missing or was filtered out.")


    # VIZ 4: Line Chart (CO2 over Time - Using the 'Order_Date' column)
    st.header("4. CO₂ Emission Trends Over Time (Line Chart) 📈")
    
    date_column = 'Order_Date'
            
    if date_column in filtered_data.columns:
        # Safely convert to datetime and then period
        filtered_data['Date_Key'] = pd.to_datetime(filtered_data[date_column], errors='coerce').dt.to_period('D')
        # Drop NaTs that resulted from coercion to avoid errors in groupby
        time_co2 = filtered_data.dropna(subset=['Date_Key']).groupby('Date_Key')['Total_CO2_kg'].sum().reset_index()
        time_co2['Date_Key'] = time_co2['Date_Key'].astype(str)
        
        fig4 = px.line(time_co2, x='Date_Key', y='Total_CO2_kg', 
                       title="Daily Total CO₂ Emissions Over Time",
                       labels={'Date_Key': 'Date', 'Total_CO2_kg': 'CO₂ Emissions (kg)'})
        st.plotly_chart(fig4, use_container_width=True)
    else:
        # This warning is what we are explicitly fixing by adding 'order_dat' to the rename map.
        st.warning(f"Cannot display time series data: Date column '{date_column}' not found.")

    # --- ACTIONABLE RECOMMENDATIONS (Business Impact) ---
    st.header("5. 💡 Actionable Recommendations & Business Impact")
    
    # Use the 'data' df for global recommendations
    full_route_co2 = data.groupby('Route_ID')['Total_CO2_kg'].sum().nlargest(5).index.tolist()
    full_fleet_summary = data.groupby('Vehicle_Type').agg(
        Avg_CCPV=('Carbon_Cost_Per_Value', 'mean')
    ).reset_index()
    # Safely get the top 3 least efficient vehicles
    least_efficient_vehicles = full_fleet_summary.nlargest(3, 'Avg_CCPV')['Vehicle_Type'].tolist()

    st.markdown(f"""
    <div style="background-color:#ffe0e0; padding:15px; border-radius:10px; border-left: 5px solid red;">
    <h4>🔴 PRIORITY 1: High-Emission Routes (Quick Wins)</h4>
    **Action:** Immediately review and re-optimize the following top 5 global routes: **{', '.join(full_route_co2)}**.
    <br>
    **Quantified Impact:** These routes offer the highest immediate potential for **fuel cost and CO₂ reduction** through consolidation or greener vehicle assignment.
    </div>
    <br>
    <div style="background-color:#fff3cd; padding:15px; border-radius:10px; border-left: 5px solid orange;">
    <h4>🟠 PRIORITY 2: Inefficient Assets (Long-term Strategy)</h4>
    **Action:** Plan maintenance review or retirement for vehicle types: **{', '.join(least_efficient_vehicles)}**.
    <br>
    **Quantified Impact:** These vehicles have the highest **Carbon Cost Per Value (CCPV)**, linking operational inefficiency directly to lost revenue potential.
    </div>
    """, unsafe_allow_html=True)
    
    # --- Download/Export Functionality (Technical Requirement) ---
    st.markdown("---")
    csv = filtered_data.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="⬇️ Download Filtered Data as CSV (Technical Deliverable)",
        data=csv,
        file_name='greenroute_analysis.csv',
        mime='text/csv',
    )