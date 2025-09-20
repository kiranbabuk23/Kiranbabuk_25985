import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
import os

# --- 1. Database Connection & Caching ---
# IMPORTANT: Replace with your actual PostgreSQL connection details.
# It is recommended to use environment variables for production.
@st.cache_data
def load_data():
    """Connects to the PostgreSQL database, queries the nonfarm_payrolls table, and caches the data."""
    try:
        conn = psycopg2.connect(
            dbname=os.environ.get("DB_NAME", "Etl_db1"),
            user=os.environ.get("DB_USER", "postgres"),
            password=os.environ.get("DB_PASSWORD", "Kiran2001##"),
            host=os.environ.get("DB_HOST", "localhost")
        )
        query = "SELECT * FROM nonfarm_payrolls;"
        df = pd.read_sql(query, conn)
        conn.close()
        
        # Ensure the date column is in datetime format
        df['date'] = pd.to_datetime(df['date'])
        
        st.success("Data loaded and cached successfully!")
        return df
    except Exception as e:
        st.error(f"Error connecting to the database or loading data: {e}")
        return None

# --- 2. Custom Styling ---
def add_custom_css():
    """Injects custom CSS for styling the app."""
    st.markdown("""
        <style>
        .main {
            background-color: #f5f5f5;
        }
        .css-1av0vzn { /* Streamlit's main header container */
            display: flex;
            justify-content: center;
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .st-emotion-cache-1q1n1p { /* CSS for the main content container */
            border-radius: 10px;
            box-shadow: 0 4px 8px 0 rgba(0,0,0,0.1), 0 6px 20px 0 rgba(0,0,0,0.1);
            padding: 20px;
            margin-bottom: 20px;
            background-color: white;
        }
        .css-1f7l053 { /* Plotly chart container */
            border-radius: 10px;
            box-shadow: 0 4px 8px 0 rgba(0,0,0,0.05), 0 6px 20px 0 rgba(0,0,0,0.05);
            padding: 10px;
            background-color: white;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            margin-top: 20px;
        }
        th, td {
            text-align: left;
            padding: 8px;
        }
        tr:nth-child(even) {
            background-color: #f2f2f2;
        }
        </style>
    """, unsafe_allow_html=True)

# --- 3. OLAP Analyses & Visualizations ---
def create_slicing_charts(df):
    """Performs and visualizes Slicing analyses."""
    st.header("Slicing Analysis")

    # Slicing 1: Average payroll employment by year (2010-2025)
    st.subheader("Average Jobs Created (Select Year Range)")
    min_year = int(df['date'].dt.year.min())
    max_year = int(df['date'].dt.year.max())
    year_range = st.slider(
        "Select year range:",
        min_value=min_year,
        max_value=max_year,
        value=(2010, 2025),
        step=1
    )
    df_avg_jobs = df[(df['date'].dt.year >= year_range[0]) & (df['date'].dt.year <= year_range[1])]
    avg_jobs_created = df_avg_jobs['total_nonfarm'].mean()
    st.metric(label=f"Average Jobs Created ({year_range[0]}-{year_range[1]})", value=f"{avg_jobs_created:,.0f}")

    # Slicing 2: Monthly employment comparison for Mar-Dec 2020 vs. 2019
    st.subheader("Monthly Employment Comparison (Mar-Dec 2020 vs. 2019)")
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month
    df_slice2 = df[((df['year'] == 2019) | (df['year'] == 2020)) & 
                   (df['month'].between(3, 12))]
    fig2 = px.line(df_slice2, x='date', y='total_nonfarm', color='year',
                   title="Monthly Employment: March-December 2020 vs. 2019",
                   labels={'total_nonfarm': 'Total Employment (in thousands)', 'date': 'Date'})
    st.plotly_chart(fig2)

def create_dicing_charts(df):
    """Performs and visualizes Dicing analyses."""
    st.header("Dicing Analysis")

    # Dicing 1: Months with > 2% month-over-month employment drop
    st.subheader("Months with > 2% Month-over-Month Employment Drop")
    df['mom_growth'] = df['total_nonfarm'].pct_change() * 100
    df['month_year'] = df['date'].dt.strftime('%b-%Y')
    
    significant_drops = df[df['mom_growth'] < -2].copy()
    if not significant_drops.empty:
        st.write("Months with a greater than 2% month-over-month employment drop:")
        st.dataframe(significant_drops[['month_year', 'mom_growth']].round(2).rename(columns={'mom_growth': 'MoM Growth (%)'}))
        
        # Calculate recovery time
        recovery_data = []
        for index, row in significant_drops.iterrows():
            drop_date = row['date']
            drop_employment = row['total_nonfarm']
            
            # Find the peak before the drop
            pre_drop_data = df[df['date'] < drop_date]
            if not pre_drop_data.empty:
                prior_peak_employment = pre_drop_data['total_nonfarm'].max()
                
                # Find the first month where employment recovers to or exceeds the prior peak
                post_drop_data = df[df['date'] > drop_date]
                recovery_month = post_drop_data[post_drop_data['total_nonfarm'] >= prior_peak_employment].first_valid_index()
                
                if recovery_month:
                    months_to_recover = (df.loc[recovery_month]['date'].year - drop_date.year) * 12 + (df.loc[recovery_month]['date'].month - drop_date.month)
                    recovery_data.append({
                        'Drop Month': row['month_year'],
                        'Prior Peak Date': df.loc[pre_drop_data['total_nonfarm'].idxmax()]['date'].strftime('%b-%Y'),
                        'Months to Recover': months_to_recover
                    })
                else:
                    recovery_data.append({'Drop Month': row['month_year'], 'Prior Peak Date': 'N/A', 'Months to Recover': 'Not recovered yet'})
        
        if recovery_data:
            st.write("Time taken to recover to the prior peak:")
            st.dataframe(pd.DataFrame(recovery_data))
    else:
        st.info("No months found with a month-over-month employment drop greater than 2%.")

    # Dicing 2: Quarterly payroll growth trends
    st.subheader("Quarterly Payroll Growth Trends by Month")
    # Calculate month-over-month percentage change for all months
    df_all = df.copy()
    df_all['year'] = df_all['date'].dt.year
    df_all['month'] = df_all['date'].dt.strftime('%b')
    df_all['month_num'] = df_all['date'].dt.month
    df_all['pct_change_mom'] = df_all['total_nonfarm'].pct_change() * 100

    # Quarter selection dropdown
    quarter_map = {
        'Q1': [1, 2, 3],
        'Q2': [4, 5, 6],
        'Q3': [7, 8, 9],
        'Q4': [10, 11, 12]
    }
    quarter = st.selectbox("Select Quarter for Analysis:", list(quarter_map.keys()), index=3)
    selected_months = quarter_map[quarter]

    # Filter for selected quarter months only
    df_quarter = df_all[df_all['month_num'].isin(selected_months)].copy()

    # Year slider
    min_year = int(df_quarter['year'].min())
    max_year = int(df_quarter['year'].max())
    year_range = st.slider(
        f"Select year range for {quarter} analysis:",
        min_value=min_year,
        max_value=max_year,
        value=(min_year, max_year),
        step=1
    )
    df_quarter_interval = df_quarter[(df_quarter['year'] >= year_range[0]) & (df_quarter['year'] <= year_range[1])]

    # Custom color mapping for months
    color_map = {
        'Q1': {'Jan': 'red', 'Feb': 'blue', 'Mar': 'green'},
        'Q2': {'Apr': 'red', 'May': 'blue', 'Jun': 'green'},
        'Q3': {'Jul': 'red', 'Aug': 'blue', 'Sep': 'green'},
        'Q4': {'Oct': 'red', 'Nov': 'blue', 'Dec': 'green'}
    }
    month_color_map = color_map[quarter]

    # Line chart: one line per month in selected quarter
    fig3 = px.line(
        df_quarter_interval,
        x='year',
        y='pct_change_mom',
        color='month',
        labels={'year': 'Year', 'pct_change_mom': 'MoM % Change', 'month': 'Month'},
        color_discrete_map=month_color_map,
        markers=True,
        title=f"{quarter} Payroll Growth Trends by Month"
    )
    st.plotly_chart(fig3, use_container_width=True)

def create_roll_up_charts(df):
    """Performs and visualizes Roll-up analyses."""
    st.header("Roll-up Analysis")

    # Roll-up 1: Quarter-over-quarter and Year-over-year growth rates
    st.subheader("Quarter-over-Quarter (Q-o-Q) Employment Analysis")

    # Quarterly aggregation
    df_quarterly = df.set_index('date').resample('QS').mean()
    df_quarterly['quarter'] = df_quarterly.index.quarter
    df_quarterly['year'] = df_quarterly.index.year
    df_quarterly['qoq_growth'] = df_quarterly['total_nonfarm'].pct_change() * 100

    # Checkbox interface for selecting quarters
    quarter_options = [1, 2, 3, 4]
    quarter_labels = [f"Q{q}" for q in quarter_options]
    selected_quarters = st.multiselect(
        "Select Quarters to Display:",
        options=quarter_options,
        default=quarter_options,
        format_func=lambda x: f"Q{x}"
    )

    # Year slider for interval selection
    min_year = int(df_quarterly['year'].min())
    max_year = int(df_quarterly['year'].max())
    year_range = st.slider(
        "Select year range for quarterly analysis:",
        min_value=min_year,
        max_value=max_year,
        value=(min_year, max_year),
        step=1
    )

    # Filter for selected quarters and year interval
    df_quarter_filtered = df_quarterly[
        (df_quarterly['quarter'].isin(selected_quarters)) &
        (df_quarterly['year'] >= year_range[0]) &
        (df_quarterly['year'] <= year_range[1])
    ].reset_index()

    # Line chart: one line per selected quarter
    fig_qoq = px.line(
        df_quarter_filtered,
        x='year',
        y='qoq_growth',
        color='quarter',
        markers=True,
        title=f"Quarter-over-Quarter Employment Growth Rate by Quarter",
        labels={'year': 'Year', 'qoq_growth': 'QoQ Growth (%)', 'quarter': 'Quarter'},
        color_discrete_map={1: 'red', 2: 'blue', 3: 'green', 4: 'orange'}
    )
    st.plotly_chart(fig_qoq)

    # Annual Analysis
    st.subheader("Annual Analysis")
    # Yearly aggregation
    df_yearly = df.set_index('date').resample('A').mean()
    df_yearly['year'] = df_yearly.index.year
    df_yearly['yoy_growth'] = df_yearly['total_nonfarm'].pct_change() * 100
    min_year_annual = int(df_yearly['year'].min())
    max_year_annual = int(df_yearly['year'].max())
    year_range_annual = st.slider(
        "Select year range for annual analysis:",
        min_value=min_year_annual,
        max_value=max_year_annual,
        value=(min_year_annual, max_year_annual),
        step=1
    )
    df_yearly_interval = df_yearly[(df_yearly['year'] >= year_range_annual[0]) & (df_yearly['year'] <= year_range_annual[1])].reset_index()
    fig_yoy = px.line(
        df_yearly_interval,
        x='year',
        y='yoy_growth',
        title="Year-over-Year Employment Growth Rate",
        labels={'year': 'Year', 'yoy_growth': 'YoY Growth (%)'}
    )
    st.plotly_chart(fig_yoy)
    
    # Roll-up 2: Compare average employment in 2010s vs. 2000s
    st.subheader("Average Employment in the 2000s vs. the 2010s")
    df['year'] = df['date'].dt.year
    decade_2000s = df[(df['year'] >= 2000) & (df['year'] <= 2009)]
    decade_2010s = df[(df['year'] >= 2010) & (df['year'] <= 2019)]
    
    avg_2000s = decade_2000s['total_nonfarm'].mean()
    avg_2010s = decade_2010s['total_nonfarm'].mean()
    
    comparison_df = pd.DataFrame({
        'Decade': ['2000s', '2010s'],
        'Average Employment': [avg_2000s, avg_2010s]
    })
    
    fig_decades = px.bar(comparison_df, x='Decade', y='Average Employment', 
                         title="Average Employment: 2000s vs. 2010s",
                         labels={'Average Employment': 'Average Employment (in thousands)'})
    st.plotly_chart(fig_decades)

def create_drill_down_charts(df):
    """Performs and visualizes Drill-down analyses."""
    st.header("Drill-down Analysis")
    
    # Drill-down 1: Year with highest annual employment gain
    st.subheader("Breakdown of Highest Annual Employment Gain")
    df_annual = df.groupby(df['date'].dt.year)['total_nonfarm'].sum().reset_index()
    df_annual['annual_gain'] = df_annual['total_nonfarm'].diff()
    df_annual.columns = ['year', 'total_employment', 'annual_gain']
    highest_gain_year = df_annual.loc[df_annual['annual_gain'].idxmax()]['year']

    st.write(f"The year with the highest annual employment gain was **{int(highest_gain_year)}**.")

    # Drill-down into that year's monthly contributions
    highest_gain_df = df[df['date'].dt.year == highest_gain_year].copy()
    highest_gain_df['month'] = highest_gain_df['date'].dt.strftime('%b')
    highest_gain_df['quarter'] = highest_gain_df['date'].dt.quarter

    # Chart above, facts below
    view_option = st.radio("View breakdown by:", options=["Month", "Quarter"], index=0)
    if view_option == "Month":
        fig_drill = px.line(
            highest_gain_df,
            x='month',
            y='total_nonfarm',
            markers=True,
            title=f"Monthly Employment Contributions in {int(highest_gain_year)}",
            labels={'total_nonfarm': 'Total Employment (in thousands)', 'month': 'Month'}
        )
    else:
        quarterly_df = highest_gain_df.groupby('quarter')['total_nonfarm'].sum().reset_index()
        fig_drill = px.line(
            quarterly_df,
            x='quarter',
            y='total_nonfarm',
            markers=True,
            title=f"Quarterly Employment Contributions in {int(highest_gain_year)}",
            labels={'total_nonfarm': 'Total Employment (in thousands)', 'quarter': 'Quarter'}
        )
    st.plotly_chart(fig_drill, use_container_width=True)

    # Facts section below chart, with CSS styling
    if int(highest_gain_year) == 2022:
        st.markdown("""
<div class="facts-section">
<strong>Facts about the USA in 2022 (Highest Employment Gain Year):</strong>
<ul>
<li><strong>Major Job Providing Sectors:</strong>
    <ul>
        <li>Healthcare & Social Assistance</li>
        <li>Professional & Business Services</li>
        <li>Leisure & Hospitality</li>
        <li>Retail Trade</li>
        <li>Construction</li>
    </ul>
</li>
<li><strong>Leading Companies Hiring in 2022:</strong>
    <ul>
        <li>Amazon</li>
        <li>Walmart</li>
        <li>CVS Health</li>
        <li>McDonald's</li>
        <li>Microsoft, Google, Apple</li>
    </ul>
</li>
<li><strong>Economic Context:</strong>
    <ul>
        <li>Strong labor market recovery post-pandemic</li>
        <li>Wage growth, especially in lower-wage sectors</li>
        <li>Remote and hybrid work models became mainstream</li>
    </ul>
</li>
</ul>
<em>Sources: U.S. Bureau of Labor Statistics, Reuters, CNBC, Bloomberg, company press releases.</em>
</div>
<style>
.facts-section {
    border: 2px solid #4F8BF9;
    border-radius: 12px;
    background: #f9fbff;
    padding: 24px 20px 16px 20px;
    margin-top: 32px;
    margin-bottom: 16px;
    box-shadow: 0 2px 8px rgba(79,139,249,0.08);
    font-size: 1.08rem;
    color: #222;
}
.facts-section strong {
    color: #4F8BF9;
    font-size: 1.15rem;
}
.facts-section ul {
    margin-left: 0.5em;
    margin-bottom: 0.5em;
}
.facts-section li {
    margin-bottom: 0.25em;
}
.facts-section em {
    color: #888;
    font-size: 0.98rem;
}
</style>
        """, unsafe_allow_html=True)
    
    # Drill-down 2: Sharpest monthly drop
    st.subheader("Sharpest Monthly Employment Drop")
    df['mom_drop'] = df['total_nonfarm'].diff()
    sharpest_drop_month = df.loc[df['mom_drop'].idxmin()]
    
    st.write(f"The sharpest drop in employment occurred in **{sharpest_drop_month['date'].strftime('%B %Y')}**.")
    st.write(f"The total payroll employment decreased by approximately **{sharpest_drop_month['mom_drop']:.2f} thousand** that month.")
    
    st.info("The available data is monthly. A weekly breakdown of this event is not possible with this dataset.")


# --- 4. Main App Structure ---
def main():
    add_custom_css()
    st.title("U.S. Non-Farm Payrolls OLAP Analysis")

    # Sidebar navigation
    st.sidebar.title("Navigation")
    menu_selection = st.sidebar.radio(
        "Select an analysis type:",
        ["Slicing", "Dicing", "Roll-up", "Drill-Down"]
    )

    data = load_data()

    if data is not None:
        if menu_selection == "Slicing":
            create_slicing_charts(data.copy())
        elif menu_selection == "Dicing":
            create_dicing_charts(data.copy())
        elif menu_selection == "Roll-up":
            create_roll_up_charts(data.copy())
        elif menu_selection == "Drill-Down":
            create_drill_down_charts(data.copy())

if __name__ == "__main__":
    main()