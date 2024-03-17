from flask import Flask, render_template
from google.cloud import bigquery

app = Flask(__name__)

# Initialize BigQuery client 
client = bigquery.Client()

@app.route('/')
def index():
    # Query the top 10 time slots with the highest trade value 
    query_top_time_slots = """
        SELECT
            time_ref,
            SUM(value) AS trade_value
        FROM
            `cloudcomputing-415709.Assignment1.GSquartely`
        GROUP BY
            time_ref
        ORDER BY
            trade_value DESC
        LIMIT
            10
    """

    # Run Query and get results

    top_time_slots_results = list(client.query(query_top_time_slots).result())

    # Query for the top 40 countries with the highest total trade deficit value
    query_top_countries_trade_deficit = """
        SELECT
            country_label,
            product_type,
            (SUM(CASE WHEN account = 'Imports' THEN value ELSE 0 END) - SUM(CASE WHEN account = 'Exports' THEN value ELSE 0 END)) AS trade_deficit_value,
            status
        FROM
            (
                SELECT
                    cc.country_label,
                    gs.product_type,
                    gs.account,
                    gs.value,
                    gs.status
                FROM
                    `cloudcomputing-415709.Assignment1.GSquartely` AS gs
                JOIN
                    `cloudcomputing-415709.Assignment1.CountryClassification` AS cc
                ON
                    gs.country_code = cc.country_code
                WHERE
                    gs.time_ref >= 201301 AND gs.time_ref <= 201512
            ) AS data_subset
        WHERE
            status = 'F'
        GROUP BY
            country_label,
            product_type,
            status
        ORDER BY
            trade_deficit_value DESC
        LIMIT
            40
    """

    # Run query and get results
    top_countries_trade_deficit_results = list(client.query(query_top_countries_trade_deficit).result())

    # Run the top_services_highest_surplus query
    top_services_highest_surplus = """
    WITH TopTimeSlots AS (
        -- Query Result 1
        SELECT
            time_ref,
            SUM(value) AS trade_value
        FROM
            `cloudcomputing-415709.Assignment1.GSquartely`
        GROUP BY
            time_ref
        ORDER BY
            trade_value DESC
        LIMIT
            10
    ),
    TopCountries AS (
        -- Query Result 2
        SELECT
            cc.country_label,
            gs.country_code,  -- Select the country_code column
            SUM(CASE WHEN gs.account = 'Imports' THEN gs.value ELSE 0 END) - SUM(CASE WHEN gs.account = 'Exports' THEN gs.value ELSE 0 END) AS trade_deficit_value,
            gs.status  -- Alias the status column
        FROM
            `cloudcomputing-415709.Assignment1.GSquartely` AS gs
        JOIN
            `cloudcomputing-415709.Assignment1.CountryClassification` AS cc
        ON
            gs.country_code = cc.country_code
        WHERE
            gs.time_ref >= 201301 AND gs.time_ref <= 201512
        GROUP BY
            cc.country_label,
            gs.country_code,  -- Group by the country_code column
            gs.status  -- Alias the status column
        ORDER BY
            trade_deficit_value DESC
        LIMIT
            40
    )
    -- Query Result 3
    SELECT
        s.service_label AS service_label,
        SUM(
            CASE WHEN g.account = 'Exports' THEN g.value ELSE -g.value END
        ) AS trade_surplus_value
    FROM
        `cloudcomputing-415709.Assignment1.GSquartely` AS g
    JOIN
        `cloudcomputing-415709.Assignment1.ServicesClassification` AS s
    ON
        g.code = s.code
    JOIN
        TopTimeSlots AS t
    ON
        g.time_ref = t.time_ref
    JOIN
        TopCountries AS c
    ON
        g.country_code = c.country_code
    WHERE
        g.status = c.status  -- Use the status from the TopCountries subquery
    GROUP BY
        s.service_label
    ORDER BY
        trade_surplus_value DESC
    LIMIT
        25
    """

    # Run the query and get results 
    
    top_services_highest_surplus_results = list(client.query(top_services_highest_surplus).result())
    return render_template('index.html', top_time_slots=top_time_slots_results, top_countries_trade_deficit=top_countries_trade_deficit_results, top_services_highest_surplus=top_services_highest_surplus_results)

if __name__ == '__main__':
    app.run(debug=True)
