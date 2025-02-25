import pandas as pd
from collections import defaultdict
import matplotlib.pyplot as plt
import seaborn as sns
import argparse
import logging
from tqdm import tqdm
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def load_networks_data(file_path):
    """
    Load networks and IPs data from CSV file
    
    Args:
        file_path (str): Path to CSV file with network data
        
    Returns:
        pandas.DataFrame: Loaded and cleaned data
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Data file not found: {file_path}")
        
    logger.info(f"Reading data from: {file_path}")
    
    try:
        df = pd.read_csv(file_path, dtype={'postal_code': str})
        
        # Filter out invalid postal codes
        valid_mask = df['postal_code'].notnull() & df['postal_code'].apply(lambda x: isinstance(x, str))
        invalid_count = (~valid_mask).sum()
        
        if invalid_count > 0:
            logger.warning(f"Filtered out {invalid_count} rows with invalid postal codes")
            
        df = df[valid_mask]
        
        logger.info(f"Loaded {len(df)} valid rows from data file")
        return df
    
    except Exception as e:
        logger.error(f"Error loading data file: {str(e)}")
        raise

def calculate_availability(df):
    """
    Calculate availability statistics by postal code
    
    Args:
        df (pandas.DataFrame): DataFrame with network data
        
    Returns:
        dict: Postal code availability statistics
    """
    postal_code_availability = defaultdict(lambda: [0, 0])
    
    logger.info("Calculating availability by postal code...")
    
    for _, row in tqdm(df.iterrows(), total=df.shape[0], desc="Processing rows"):
        postal_code = row['postal_code']
        reachable = row['reachable']
        
        postal_code_availability[postal_code][0] += reachable
        postal_code_availability[postal_code][1] += 1
    
    # Calculate and log percentages
    logger.info("Availability percentages by postal code:")
    for postal_code, (reachable, total) in sorted(postal_code_availability.items()):
        percentage = (reachable / total) * 100
        logger.info(f"Postal Code: {postal_code}, Availability: {percentage:.2f}%")
    
    return postal_code_availability

def visualize_basic_bar(postal_code_availability, output_file=None, min_threshold=0, max_codes=50):
    """
    Create basic bar chart of availability by postal code
    
    Args:
        postal_code_availability (dict): Postal code availability statistics
        output_file (str): Path to save visualization
        min_threshold (float): Minimum threshold for response rate
        max_codes (int): Maximum number of postal codes to include
    """
    data = []
    
    for postal_code, (reachable, total) in postal_code_availability.items():
        percentage = (reachable / total) * 100
        if percentage >= min_threshold:
            data.append((postal_code, percentage))
    
    # Sort by percentage (descending) and limit to max_codes
    data.sort(key=lambda x: x[1], reverse=True)
    if max_codes and len(data) > max_codes:
        logger.info(f"Limiting visualization to top {max_codes} postal codes")
        data = data[:max_codes]
    
    if not data:
        logger.warning("No postal codes with response rates above threshold")
        return
    
    postal_codes, percentages = zip(*data)
    
    plt.figure(figsize=(15, 8))
    plt.bar(postal_codes, percentages)
    plt.xlabel('Postal Codes')
    plt.ylabel('Availability (%)')
    plt.title('Network Availability by Postal Code')
    plt.xticks(rotation=90)
    plt.tight_layout()
    
    if output_file:
        plt.savefig(output_file, bbox_inches='tight')
        logger.info(f"Saved bar chart to {output_file}")
    else:
        plt.show()

def visualize_heatmap(postal_code_availability, output_file=None, min_threshold=0):
    """
    Create heatmap visualization of availability by postal code
    
    Args:
        postal_code_availability (dict): Postal code availability statistics
        output_file (str): Path to save visualization
        min_threshold (float): Minimum threshold for response rate
    """
    postal_codes = []
    availability_percentages = []
    
    for postal_code, (reachable, total) in postal_code_availability.items():
        percentage = (reachable / total) * 100
        if percentage >= min_threshold:
            postal_codes.append(postal_code)
            availability_percentages.append(percentage)
    
    if not postal_codes:
        logger.warning("No postal codes with response rates above threshold")
        return
    
    # Create DataFrame for heatmap
    availability_data = pd.DataFrame({
        'postal_code': postal_codes, 
        'availability': availability_percentages
    })
    
    # Create a pivot table of the data
    pivot_data = availability_data.pivot_table(
        values='availability',
        index=None, 
        columns='postal_code',
        aggfunc='mean'
    ).T
    
    plt.figure(figsize=(16, 10))
    
    # Create the heatmap
    sns.heatmap(
        pivot_data, 
        cmap='viridis', 
        cbar_kws={'label': 'Availability (%)'},
        annot=True,
        fmt='.1f'
    )
    
    plt.title('Network Availability by Postal Code')
    plt.tight_layout()
    
    if output_file:
        plt.savefig(output_file, bbox_inches='tight')
        logger.info(f"Saved heatmap to {output_file}")
    else:
        plt.show()

def main():
    """Main function with argument parsing"""
    parser = argparse.ArgumentParser(description='Visualize network availability by postal code')
    parser.add_argument('--input', '-i', default='networks_and_ips.csv', help='Input CSV file path')
    parser.add_argument('--output', '-o', help='Output file for visualization')
    parser.add_argument('--min-threshold', '-t', type=float, default=0, help='Minimum response rate threshold for visualization')
    parser.add_argument('--max-codes', '-m', type=int, default=50, help='Maximum number of postal codes to display')
    parser.add_argument('--viz-type', '-v', choices=['bar', 'heatmap'], default='bar', help='Visualization type')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    try:
        # Load data
        df = load_networks_data(args.input)
        
        # Calculate availability
        postal_code_availability = calculate_availability(df)
        
        # Create visualization
        if args.viz_type == 'bar':
            visualize_basic_bar(
                postal_code_availability, 
                output_file=args.output,
                min_threshold=args.min_threshold,
                max_codes=args.max_codes
            )
        else:  # heatmap
            visualize_heatmap(
                postal_code_availability, 
                output_file=args.output,
                min_threshold=args.min_threshold
            )
        
        logger.info("Visualization completed successfully")
        return postal_code_availability
    
    except Exception as e:
        logger.error(f"Error during execution: {str(e)}")
        raise

if __name__ == "__main__":
    main()