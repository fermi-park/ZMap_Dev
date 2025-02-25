import csv
import subprocess
import ipaddress
import os
import argparse
import logging
from collections import defaultdict
from tqdm import tqdm
import matplotlib.pyplot as plt
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def get_zmap_scan_results(networks_file, output_file=None, bandwidth="10M", port=80, simulation_mode=True):
    """
    Run ZMap scan on specified networks with configurable parameters
    
    Args:
        networks_file (str): Path to file containing networks to scan
        output_file (str): Path to save scan results (defaults to stdout)
        bandwidth (str): Bandwidth cap for ZMap
        port (int): Port to scan
        simulation_mode (bool): If True, simulate scan results instead of running ZMap
        
    Returns:
        set: Set of responsive IP addresses
    """
    if not os.path.exists(networks_file):
        raise FileNotFoundError(f"Networks file not found: {networks_file}")
    
    # Simulation mode for testing without ZMap
    if simulation_mode:
        logger.info("Running in simulation mode - generating mock ZMap results")
        # Read networks and generate simulated responses (25% response rate)
        reachable_ips = set()
        with open(networks_file, 'r') as f:
            networks = f.read().strip().split('\n')
            
            for network_str in networks:
                if not network_str:
                    continue
                    
                try:
                    network = ipaddress.ip_network(network_str)
                    # For each IP in the network, add it to results with 25% probability
                    for i, ip in enumerate(network.hosts()):
                        # Limit to first 10 IPs per network for performance
                        if i >= 10:
                            break
                            
                        # Simulate 25% response rate
                        if i % 4 == 0:  
                            reachable_ips.add(str(ip))
                except Exception as e:
                    logger.warning(f"Error in simulation for network {network_str}: {str(e)}")
        
        logger.info(f"Simulation generated {len(reachable_ips)} responsive IPs")
        return reachable_ips
                
    # Real ZMap scan mode
    output_param = ["-o", output_file] if output_file else ["-o", "-"]
    
    cmd = [
        "zmap", 
        "-p", str(port), 
        "-B", bandwidth,
        "-w", networks_file
    ] + output_param
    
    logger.info(f"Starting ZMap scan using command: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        logger.info("ZMap scan completed successfully")
        return set(result.stdout.strip().split("\n"))
    except subprocess.CalledProcessError as e:
        logger.error(f"ZMap scan failed: {e.stderr}")
        raise

def is_local_network(network):
    """Check if network is local/private"""
    for ip in network.hosts():
        if ip.is_private or ip.is_loopback:
            return True
    return False

def process_input_csv(input_file, max_networks=None):
    """
    Process input CSV file with network and postal code data
    
    Args:
        input_file (str): Path to input CSV file
        max_networks (int): Maximum number of networks to process
        
    Returns:
        tuple: List of networks and dict mapping networks to postal codes
    """
    networks = []
    postal_codes = {}
    
    logger.info(f"Reading CSV file: {input_file}")
    
    try:
        with open(input_file, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            row_count = 0
            
            for row in tqdm(reader, desc="Processing networks"):
                if max_networks and row_count >= max_networks:
                    break
                
                network = row.get('network')
                postal_code = row.get('postal_code')
                
                if not network or not postal_code:
                    logger.warning(f"Missing network or postal code in row: {row}")
                    continue
                
                try:
                    ip_network = ipaddress.ip_network(network)
                    
                    if is_local_network(ip_network):
                        logger.debug(f"Skipping local network: {network}")
                        continue
                    
                    networks.append(str(ip_network))
                    postal_codes[str(ip_network)] = postal_code
                
                except ValueError:
                    logger.warning(f"Invalid network format: {network}")
                
                row_count += 1
        
        logger.info(f"Processed {row_count} networks from CSV file")
        return networks, postal_codes
    
    except FileNotFoundError:
        logger.error(f"Input file not found: {input_file}")
        raise

def calculate_availability(networks, postal_codes, reachable_ips):
    """
    Calculate availability percentages by postal code
    
    Args:
        networks (list): List of network strings
        postal_codes (dict): Mapping of networks to postal codes
        reachable_ips (set): Set of reachable IP addresses
        
    Returns:
        dict: Postal code availability statistics
    """
    postal_code_availability = defaultdict(lambda: [0, 0])
    networks_and_ips = []
    
    logger.info("Calculating availability percentages...")
    
    for network_str in tqdm(networks, desc="Processing networks"):
        network = ipaddress.ip_network(network_str)
        postal_code = postal_codes[network_str]
        
        for ip in network.hosts():
            ip_str = str(ip)
            is_reachable = ip_str in reachable_ips
            
            # Record for CSV export
            networks_and_ips.append({
                'network': network_str,
                'ip': ip_str,
                'postal_code': postal_code,
                'reachable': 1 if is_reachable else 0
            })
            
            if is_reachable:
                postal_code_availability[postal_code][0] += 1
            postal_code_availability[postal_code][1] += 1
    
    # Save the detailed results
    df = pd.DataFrame(networks_and_ips)
    df.to_csv('networks_and_ips.csv', index=False)
    logger.info("Saved detailed results to networks_and_ips.csv")
    
    return postal_code_availability

def visualize_response_rates(postal_code_availability, output_file=None, min_threshold=0):
    """
    Visualize response rates by postal code
    
    Args:
        postal_code_availability (dict): Postal code availability statistics
        output_file (str): Path to save the visualization
        min_threshold (float): Minimum response rate to include in visualization
    """
    postal_codes = []
    response_rates = []
    
    for postal_code, (reachable, total) in postal_code_availability.items():
        percentage = (reachable / total) * 100
        if percentage >= min_threshold:
            postal_codes.append(postal_code)
            response_rates.append(percentage)
    
    if not postal_codes:
        logger.warning("No postal codes with response rates above threshold")
        return
    
    plt.figure(figsize=(15, 6))
    plt.bar(postal_codes, response_rates)
    plt.xlabel('Postal Codes')
    plt.ylabel('Response Rate (%)')
    plt.title('Response Rates by Postal Code')
    plt.xticks(rotation=90)
    
    if output_file:
        plt.savefig(output_file, bbox_inches='tight')
        logger.info(f"Saved visualization to {output_file}")
    else:
        plt.show()

def main():
    """Main function with argument parsing"""
    parser = argparse.ArgumentParser(description='Network availability analysis by postal code')
    parser.add_argument('--input', '-i', required=True, help='Input CSV file path')
    parser.add_argument('--output', '-o', help='Output file for visualization')
    parser.add_argument('--max-networks', '-m', type=int, help='Maximum number of networks to process')
    parser.add_argument('--port', '-p', type=int, default=80, help='Port to scan (default: 80)')
    parser.add_argument('--bandwidth', '-b', default='10M', help='ZMap bandwidth cap (default: 10M)')
    parser.add_argument('--networks-file', default='networks.txt', help='File to save networks list')
    parser.add_argument('--min-threshold', '-t', type=float, default=0, help='Minimum response rate threshold for visualization')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    try:
        # Process input CSV
        networks, postal_codes = process_input_csv(args.input, args.max_networks)
        
        # Write networks to file
        with open(args.networks_file, "w") as f:
            f.write("\n".join(networks))
        logger.info(f"Saved {len(networks)} networks to {args.networks_file}")
        
        # Run ZMap scan
        reachable_ips = get_zmap_scan_results(
            args.networks_file, 
            port=args.port, 
            bandwidth=args.bandwidth
        )
        
        # Calculate availability
        postal_code_availability = calculate_availability(networks, postal_codes, reachable_ips)
        
        # Print results
        logger.info("Postal Code Availability Results:")
        for postal_code, (reachable, total) in postal_code_availability.items():
            percentage = (reachable / total) * 100
            logger.info(f"Postal Code: {postal_code}, Availability: {percentage:.2f}%")
        
        # Visualize results
        visualize_response_rates(
            postal_code_availability, 
            output_file=args.output,
            min_threshold=args.min_threshold
        )
        
        logger.info("Script execution completed successfully")
        return postal_code_availability
    
    except Exception as e:
        logger.error(f"Error during execution: {str(e)}")
        raise

if __name__ == "__main__":
    postal_code_availability = main()