import os
from fastapi import FastAPI
from mcp.server.fastapi import FastApiMcpServer
from mcp.types import Tool, TextContent
from google.cloud import bigquery

# Initialize FastAPI app and MCP Server
app = FastAPI(title="BigQuery MCP Server")
mcp_server = FastApiMcpServer(
    name="bigquery-updater", 
    version="1.0.0"
)

# Initialize BigQuery Client (Uses Cloud Run's Service Account credentials automatically)
bq_client = bigquery.Client()

# Define the target table using environment variables
PROJECT_ID = os.getenv("GCP_PROJECT_ID")
DATASET_ID = os.getenv("BQ_DATASET_ID")
TABLE_ID = f"{PROJECT_ID}.{DATASET_ID}.extracted_invoices"

@mcp_server.tool(
    name="update_invoice_table",
    description="Inserts extracted invoice details into the BigQuery warehouse database."
)
async def update_invoice_table(
    vendor_name: str,
    invoice_number: str,
    invoice_date: str,  # Expected format: YYYY-MM-DD
    tax: float,
    total_cost: float
) -> list[TextContent]:
    
    # Construct the parameterized SQL query to prevent SQL injection
    query = f"""
        INSERT INTO `{TABLE_ID}` (vendor_name, invoice_number, invoice_date, tax, total_cost)
        VALUES (@vendor_name, @invoice_number, PARSE_DATE('%Y-%m-%d', @invoice_date), @tax, @total_cost)
    """
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("vendor_name", "STRING", vendor_name),
            bigquery.ScalarQueryParameter("invoice_number", "STRING", invoice_number),
            bigquery.ScalarQueryParameter("invoice_date", "STRING", invoice_date),
            bigquery.ScalarQueryParameter("tax", "NUMERIC", tax),
            bigquery.ScalarQueryParameter("total_cost", "NUMERIC", total_cost),
        ]
    )

    try:
        # Execute the query
        query_job = bq_client.query(query, job_config=job_config)
        query_job.result()  # Wait for the statement to finish running
        
        return [TextContent(type="text", text=f"Successfully updated BigQuery. Row inserted for invoice {invoice_number} from {vendor_name}.")]
        
    except Exception as e:
        return [TextContent(type="text", text=f"Failed to update BigQuery. Error: {str(e)}")]

# Mount the MCP protocol routes onto the FastAPI application
app.include_router(mcp_server.router)
