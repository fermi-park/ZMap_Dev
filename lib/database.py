import os
import logging
import psycopg2
from psycopg2.extras import execute_values
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Manages database connections and operations for ZMap scanner results
    """
    def __init__(self):
        """Initialize database connection parameters from environment variables"""
        self.db_params = {
            'host': os.environ.get('DB_HOST', 'localhost'),
            'port': os.environ.get('DB_PORT', '5432'),
            'database': os.environ.get('DB_NAME', 'zmap_scanner'),
            'user': os.environ.get('DB_USER', 'zmap'),
            'password': os.environ.get('DB_PASSWORD', 'zmappassword'),
        }
        self.initialized = False
        
    @contextmanager
    def get_connection(self):
        """Create and yield a database connection"""
        connection = None
        try:
            connection = psycopg2.connect(**self.db_params)
            yield connection
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            raise
        finally:
            if connection:
                connection.close()
                
    def initialize_database(self):
        """Create necessary tables if they don't exist"""
        if self.initialized:
            return
            
        create_tables_query = """
        -- Create scans table to track scan metadata
        CREATE TABLE IF NOT EXISTS scans (
            scan_id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            port INTEGER,
            parameters JSONB,
            scan_type VARCHAR(50),
            description TEXT
        );
        
        -- Create networks table to store network information
        CREATE TABLE IF NOT EXISTS networks (
            network_id SERIAL PRIMARY KEY,
            scan_id INTEGER REFERENCES scans(scan_id),
            network CIDR NOT NULL,
            postal_code VARCHAR(20),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Create scan_results table to store individual scan results
        CREATE TABLE IF NOT EXISTS scan_results (
            result_id SERIAL PRIMARY KEY,
            scan_id INTEGER REFERENCES scans(scan_id),
            network_id INTEGER REFERENCES networks(network_id),
            ip INET NOT NULL,
            postal_code VARCHAR(20),
            reachable BOOLEAN,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Create a view for easy querying of availability by postal code
        CREATE OR REPLACE VIEW postal_code_availability AS
        SELECT
            sr.scan_id,
            sr.postal_code,
            COUNT(CASE WHEN sr.reachable THEN 1 END) AS reachable_count,
            COUNT(*) AS total_count,
            (COUNT(CASE WHEN sr.reachable THEN 1 END)::FLOAT / COUNT(*)::FLOAT) * 100 AS response_rate,
            s.timestamp
        FROM
            scan_results sr
        JOIN
            scans s ON sr.scan_id = s.scan_id
        GROUP BY
            sr.scan_id, sr.postal_code, s.timestamp
        ORDER BY
            s.timestamp DESC, response_rate DESC;
        """
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(create_tables_query)
                conn.commit()
            self.initialized = True
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization error: {str(e)}")
            raise

    def create_scan(self, port, scan_type="zmap", parameters=None, description=None):
        """
        Create a new scan record
        
        Args:
            port: The port that was scanned
            scan_type: Type of scan (zmap, simulation)
            parameters: Dictionary of scan parameters
            description: Human-readable description of the scan
            
        Returns:
            int: scan_id of the created scan
        """
        self.initialize_database()
        
        query = """
        INSERT INTO scans (port, scan_type, parameters, description)
        VALUES (%s, %s, %s, %s)
        RETURNING scan_id
        """
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (port, scan_type, parameters, description))
                    scan_id = cursor.fetchone()[0]
                conn.commit()
            logger.info(f"Created new scan with ID: {scan_id}")
            return scan_id
        except Exception as e:
            logger.error(f"Error creating scan: {str(e)}")
            raise
            
    def save_networks(self, scan_id, networks_data):
        """
        Save networks with postal codes
        
        Args:
            scan_id: The ID of the scan
            networks_data: List of dictionaries with network and postal_code
            
        Returns:
            dict: Mapping of network strings to network_ids
        """
        self.initialize_database()
        
        query = """
        INSERT INTO networks (scan_id, network, postal_code)
        VALUES %s
        RETURNING network_id, network
        """
        
        try:
            network_values = [(scan_id, net['network'], net['postal_code']) for net in networks_data]
            network_map = {}
            
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    execute_values(cursor, query, network_values)
                    results = cursor.fetchall()
                    for network_id, network in results:
                        network_map[str(network)] = network_id
                conn.commit()
                
            logger.info(f"Saved {len(networks_data)} networks for scan {scan_id}")
            return network_map
        except Exception as e:
            logger.error(f"Error saving networks: {str(e)}")
            raise
            
    def save_scan_results(self, scan_id, results_data):
        """
        Save scan results
        
        Args:
            scan_id: The ID of the scan
            results_data: List of dictionaries with network_id, ip, postal_code, reachable
            
        Returns:
            int: Number of results saved
        """
        self.initialize_database()
        
        query = """
        INSERT INTO scan_results (scan_id, network_id, ip, postal_code, reachable)
        VALUES %s
        """
        
        try:
            # Batch results into chunks to avoid memory issues
            batch_size = 5000
            for i in range(0, len(results_data), batch_size):
                batch = results_data[i:i+batch_size]
                values = [(
                    scan_id, 
                    result['network_id'], 
                    result['ip'], 
                    result['postal_code'], 
                    result['reachable']
                ) for result in batch]
                
                with self.get_connection() as conn:
                    with conn.cursor() as cursor:
                        execute_values(cursor, query, values)
                    conn.commit()
                
            logger.info(f"Saved {len(results_data)} scan results for scan {scan_id}")
            return len(results_data)
        except Exception as e:
            logger.error(f"Error saving scan results: {str(e)}")
            raise
            
    def get_postal_code_availability(self, scan_id=None):
        """
        Get availability statistics by postal code
        
        Args:
            scan_id: Optional scan ID to filter by
            
        Returns:
            list: List of dictionaries with postal code statistics
        """
        self.initialize_database()
        
        if scan_id:
            query = """
            SELECT 
                postal_code, 
                reachable_count, 
                total_count, 
                response_rate,
                timestamp
            FROM 
                postal_code_availability
            WHERE 
                scan_id = %s
            ORDER BY 
                response_rate DESC
            """
            params = (scan_id,)
        else:
            query = """
            SELECT 
                scan_id,
                postal_code, 
                reachable_count, 
                total_count, 
                response_rate,
                timestamp
            FROM 
                postal_code_availability
            ORDER BY 
                timestamp DESC, 
                response_rate DESC
            """
            params = None
            
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)
                    columns = [desc[0] for desc in cursor.description]
                    results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            return results
        except Exception as e:
            logger.error(f"Error retrieving postal code availability: {str(e)}")
            raise
            
    def get_latest_scan_id(self):
        """
        Get the latest scan ID
        
        Returns:
            int: Latest scan ID
        """
        self.initialize_database()
        
        query = "SELECT scan_id FROM scans ORDER BY timestamp DESC LIMIT 1"
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    result = cursor.fetchone()
                    return result[0] if result else None
        except Exception as e:
            logger.error(f"Error retrieving latest scan ID: {str(e)}")
            raise