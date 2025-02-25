#!/usr/bin/env python3
import os
import json
import logging
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import subprocess
import sys
import boto3
from datetime import datetime

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from lib.database import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="ZMap Scanner API",
    description="API for ZMap network scanner results",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific frontend origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database manager
db = DatabaseManager()

# Pydantic models for request/response validation
class ScanRequest(BaseModel):
    input_file: str = Field(..., description="Path to input CSV file")
    max_networks: Optional[int] = Field(None, description="Maximum number of networks to process")
    port: int = Field(80, description="Port to scan")
    bandwidth: str = Field("10M", description="ZMap bandwidth cap")
    simulate: bool = Field(False, description="Run in simulation mode")
    description: Optional[str] = Field(None, description="Description of the scan")

class ScanResponse(BaseModel):
    scan_id: int
    timestamp: str
    status: str
    message: str

class PostalCodeStats(BaseModel):
    postal_code: str
    reachable_count: int
    total_count: int
    response_rate: float
    timestamp: str

class AvailabilityResponse(BaseModel):
    scan_id: int
    results: List[PostalCodeStats]

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.post("/scans", response_model=ScanResponse)
def create_scan(scan_request: ScanRequest, background_tasks: BackgroundTasks):
    """
    Create a new scan and run it in the background
    
    This endpoint initiates a new ZMap scan based on the provided parameters.
    The scan runs asynchronously, and results can be retrieved later.
    """
    try:
        # Store scan parameters in the database
        parameters = {
            "input_file": scan_request.input_file,
            "max_networks": scan_request.max_networks,
            "bandwidth": scan_request.bandwidth,
            "simulate": scan_request.simulate
        }
        
        scan_type = "simulation" if scan_request.simulate else "zmap"
        scan_id = db.create_scan(
            port=scan_request.port,
            scan_type=scan_type,
            parameters=json.dumps(parameters),
            description=scan_request.description
        )
        
        # Run the scan in the background
        background_tasks.add_task(
            run_scan,
            scan_id=scan_id,
            input_file=scan_request.input_file,
            max_networks=scan_request.max_networks,
            port=scan_request.port,
            bandwidth=scan_request.bandwidth,
            simulate=scan_request.simulate
        )
        
        return {
            "scan_id": scan_id,
            "timestamp": datetime.now().isoformat(),
            "status": "queued",
            "message": "Scan queued for execution"
        }
    except Exception as e:
        logger.error(f"Error creating scan: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating scan: {str(e)}")

@app.get("/scans/{scan_id}/availability", response_model=List[Dict[str, Any]])
def get_scan_availability(scan_id: int):
    """
    Get availability statistics by postal code for a specific scan
    
    This endpoint retrieves the processed results of a previously run scan,
    showing response rates by postal code.
    """
    try:
        results = db.get_postal_code_availability(scan_id)
        if not results:
            raise HTTPException(status_code=404, detail=f"No results found for scan {scan_id}")
        return results
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error retrieving scan availability: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving scan availability: {str(e)}")

@app.get("/availability", response_model=List[Dict[str, Any]])
def get_all_availability():
    """
    Get availability statistics for all scans
    
    This endpoint retrieves results from all scans, sorted by recency.
    """
    try:
        results = db.get_postal_code_availability()
        return results
    except Exception as e:
        logger.error(f"Error retrieving availability data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving availability data: {str(e)}")

@app.get("/scans/{scan_id}")
def get_scan(scan_id: int):
    """
    Get information about a specific scan
    
    This endpoint retrieves metadata about a specific scan,
    including parameters and execution status.
    """
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT scan_id, timestamp, port, scan_type, parameters, description FROM scans WHERE scan_id = %s",
                    (scan_id,)
                )
                result = cursor.fetchone()
                
                if not result:
                    raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")
                
                columns = [desc[0] for desc in cursor.description]
                scan_info = dict(zip(columns, result))
                
                # Get counts for this scan
                cursor.execute(
                    "SELECT COUNT(*) FROM scan_results WHERE scan_id = %s",
                    (scan_id,)
                )
                result_count = cursor.fetchone()[0]
                scan_info['result_count'] = result_count
                
                # Get network count
                cursor.execute(
                    "SELECT COUNT(*) FROM networks WHERE scan_id = %s",
                    (scan_id,)
                )
                network_count = cursor.fetchone()[0]
                scan_info['network_count'] = network_count
                
                return scan_info
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error retrieving scan: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving scan: {str(e)}")

@app.get("/scans")
def list_scans():
    """
    List all scans
    
    This endpoint retrieves a list of all scans that have been run,
    with basic metadata.
    """
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT scan_id, timestamp, port, scan_type, description FROM scans ORDER BY timestamp DESC"
                )
                columns = [desc[0] for desc in cursor.description]
                scans = [dict(zip(columns, row)) for row in cursor.fetchall()]
                return scans
    except Exception as e:
        logger.error(f"Error listing scans: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing scans: {str(e)}")

def run_scan(scan_id: int, input_file: str, max_networks: Optional[int], port: int, bandwidth: str, simulate: bool):
    """
    Run a ZMap scan with the specified parameters
    
    This function is called in the background to execute the scan
    and store the results in the database.
    """
    try:
        logger.info(f"Starting scan {scan_id} with parameters: port={port}, bandwidth={bandwidth}, simulate={simulate}")
        
        # Import the scanner module from the parent directory
        import sys
        import os
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        
        # Import scanner module to run the scan
        from Scripts.zmap_postal_code_availability import process_input_csv, get_zmap_scan_results, is_local_network
        import ipaddress
        
        # Process input CSV
        networks, postal_codes = process_input_csv(input_file, max_networks)
        
        # Save networks to database
        network_data = [{"network": net, "postal_code": postal_codes[net]} for net in networks]
        network_map = db.save_networks(scan_id, network_data)
        
        # Create temporary networks file
        networks_file = f"/tmp/networks_{scan_id}.txt"
        with open(networks_file, "w") as f:
            f.write("\n".join(networks))
        
        # Run ZMap scan
        reachable_ips = get_zmap_scan_results(
            networks_file,
            port=port,
            bandwidth=bandwidth,
            simulation_mode=simulate
        )
        
        # Process and save results
        results_data = []
        for network_str in networks:
            network = ipaddress.ip_network(network_str)
            postal_code = postal_codes[network_str]
            network_id = network_map[network_str]
            
            for ip in network.hosts():
                ip_str = str(ip)
                is_reachable = ip_str in reachable_ips
                
                # Add to results
                results_data.append({
                    'network_id': network_id,
                    'ip': ip_str,
                    'postal_code': postal_code,
                    'reachable': is_reachable
                })
        
        # Save results to database
        db.save_scan_results(scan_id, results_data)
        
        # Cleanup
        if os.path.exists(networks_file):
            os.remove(networks_file)
        
        logger.info(f"Scan {scan_id} completed successfully")
        
        # If AWS is configured, copy results to S3
        if os.environ.get('AWS_ACCESS_KEY_ID') and os.environ.get('S3_BUCKET'):
            upload_results_to_s3(scan_id)
    
    except Exception as e:
        logger.error(f"Error running scan {scan_id}: {str(e)}")
        # Update scan status to failed
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE scans SET description = %s WHERE scan_id = %s",
                    (f"FAILED: {str(e)}", scan_id)
                )
            conn.commit()

def upload_results_to_s3(scan_id: int):
    """Upload scan results to S3 bucket"""
    try:
        s3_bucket = os.environ.get('S3_BUCKET')
        if not s3_bucket:
            logger.warning("S3_BUCKET not configured, skipping S3 upload")
            return
        
        # Get scan info
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT timestamp, port, scan_type FROM scans WHERE scan_id = %s",
                    (scan_id,)
                )
                result = cursor.fetchone()
                if not result:
                    logger.warning(f"Scan {scan_id} not found, skipping S3 upload")
                    return
                
                timestamp, port, scan_type = result
        
        # Initialize S3 client
        s3 = boto3.client('s3')
        
        # Export scan results to CSV
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        n.network,
                        sr.ip,
                        sr.postal_code,
                        sr.reachable
                    FROM
                        scan_results sr
                    JOIN
                        networks n ON sr.network_id = n.network_id
                    WHERE
                        sr.scan_id = %s
                    """,
                    (scan_id,)
                )
                
                columns = [desc[0] for desc in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        # Create CSV file
        csv_file = f"/tmp/scan_{scan_id}_results.csv"
        with open(csv_file, 'w') as f:
            f.write(','.join(columns) + '\n')
            for row in results:
                f.write(','.join([str(row[col]) for col in columns]) + '\n')
        
        # Upload to S3
        timestamp_str = timestamp.strftime('%Y%m%d_%H%M%S')
        s3_key = f"results/scan_{scan_id}_{timestamp_str}.csv"
        s3.upload_file(csv_file, s3_bucket, s3_key)
        
        # Upload availability stats
        availability = db.get_postal_code_availability(scan_id)
        json_file = f"/tmp/scan_{scan_id}_availability.json"
        with open(json_file, 'w') as f:
            json.dump(availability, f)
        
        s3_key = f"results/scan_{scan_id}_{timestamp_str}_availability.json"
        s3.upload_file(json_file, s3_bucket, s3_key)
        
        # Cleanup
        os.remove(csv_file)
        os.remove(json_file)
        
        logger.info(f"Scan {scan_id} results uploaded to S3 bucket {s3_bucket}")
    
    except Exception as e:
        logger.error(f"Error uploading results to S3: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("API_PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)