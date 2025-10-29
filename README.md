🌿 NexGen GreenRoute: Logistics Sustainability Tracker

Challenge: Innovation in Logistics and Sustainability (Sustainability Tracker - Option 7)
Goal: To create a data-driven dashboard that quantifies the environmental impact of logistics operations and provides clear, actionable steps for reducing the carbon footprint while maintaining cost efficiency.

🚀 Getting Started

This application is built with Python and deployed as an interactive web application using Streamlit.

1. Prerequisites

Ensure you have Python installed (Python 3.8+ recommended).

2. File Structure

The application requires the following files to be present in the root directory:

run_app.py (The main application code)

requirements.txt (List of dependencies)

orders.csv

routes_distance.csv

vehicle_fleet.csv

delivery_performance.csv

cost_breakdown.csv

3. Installation

Navigate to the project directory in your terminal.

Install the required libraries using the requirements.txt file:

pip install -r requirements.txt


4. Run the Application

Execute the following command to start the Streamlit application:

streamlit run run_app.py


The application will launch in your default web browser at http://localhost:8501.

💡 Methodology and Key Metrics

The dashboard integrates and cleans data from the five provided datasets (orders.csv, cost_breakdown.csv, etc.) to derive actionable insights.

Data Cleaning & Handling

Standardization: All column names were systematically cleaned (lowercased, whitespace removed) to ensure robust merging across all datasets, specifically fixing inconsistencies like Order_Dat $\to$ Order_Date and Origin $\to$ Origins.

Missing Value Imputation: For critical calculation fields (distance_km, co2_emissions_kg_per_km), missing values were handled by imputation with the mean to prevent data loss and ensure the $\text{CO}_2$ calculation could run end-to-end.

Error Handling: Robust error trapping was implemented during data loading to prevent the application from crashing if key files or required columns are missing.

Core Derived Metrics

Metric

Calculation (Formula)

Business Insight

Total $\text{CO}_2$ (kg)

$$\text{Distance (km)} \times \text{CO}_2 \text{ Emissions (kg/km)}$$

The primary measure of environmental impact.

Carbon Cost Per Value (CCPV)

$$\text{Total } \text{CO}_2 \text{ (kg)} / \text{Order Value (USD)}$$

Innovation KPI: Measures the carbon efficiency per unit of revenue. A lower CCPV indicates a greener, more cost-effective operation. This connects sustainability directly to the bottom line.

📈 Dashboard Features & Visualization

The dashboard is fully interactive, with two sidebar filters for Vehicle Type and Order Priority.

Key Visualizations

VIZ 1 (Bar Chart): $\text{CO}_2$ Hotspot Analysis - Pinpoints the top 10 most polluting routes, guiding immediate re-routing efforts.

VIZ 2 (Scatter Plot): Fleet Asset Performance - Maps Average Vehicle Age against Average CCPV. Bubble size shows total $\text{CO}_2$, helping prioritize maintenance or retirement of older, less efficient, and high-impact vehicles.

VIZ 3 (Pie Chart): $\text{CO}_2$ Distribution by Origin - Shows the percentage contribution of emissions by warehouse, guiding infrastructure investment.

VIZ 4 (Line Chart): Emission Trends Over Time - Tracks daily $\text{CO}_2$ to monitor the success of optimization efforts and identify seasonal spikes.

Actionable Recommendations

The dashboard automatically generates two priority recommendations based on the global dataset:

🔴 PRIORITY 1: High-Emission Routes: Recommends immediate review for the top 5 global $\text{CO}_2$ emitting routes for quick-win optimization.

🟠 PRIORITY 2: Inefficient Assets: Recommends long-term strategy (maintenance/retirement) for vehicle types identified with the highest CCPV, directly improving profit and sustainability simultaneously.

Technical Deliverable: The dashboard includes a Download Filtered Data as CSV button to allow users to export the current view for deeper analysis.