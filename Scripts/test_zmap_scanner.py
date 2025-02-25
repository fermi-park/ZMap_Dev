import unittest
import os
import tempfile
import pandas as pd
from unittest.mock import patch, MagicMock
import sys
import ipaddress
from io import StringIO

# Fix import path for testing
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Import the modules to test
from zmap_postal_code_availability import (
    is_local_network,
    process_input_csv,
    get_zmap_scan_results,
    calculate_availability
)
from zmap_visualizing_response_rate import (
    load_networks_data,
    calculate_availability as viz_calculate_availability
)

class TestZMapScanner(unittest.TestCase):
    """Test suite for ZMap Scanner functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a temporary CSV file with test data
        self.test_csv_file = tempfile.NamedTemporaryFile(delete=False, suffix='.csv')
        test_data = pd.DataFrame({
            'network': ['192.168.1.0/24', '10.0.0.0/24', '172.16.0.0/16', '8.8.8.0/24'],
            'postal_code': ['12345', '67890', '54321', '98765']
        })
        test_data.to_csv(self.test_csv_file.name, index=False)
        
        # Create a temporary networks_and_ips.csv file
        self.test_networks_file = tempfile.NamedTemporaryFile(delete=False, suffix='.csv')
        networks_data = pd.DataFrame({
            'network': ['8.8.8.0/24', '8.8.8.0/24', '8.8.8.0/24'],
            'ip': ['8.8.8.1', '8.8.8.2', '8.8.8.3'],
            'postal_code': ['98765', '98765', '98765'],
            'reachable': [1, 0, 1]
        })
        networks_data.to_csv(self.test_networks_file.name, index=False)
    
    def tearDown(self):
        """Tear down test fixtures"""
        os.unlink(self.test_csv_file.name)
        os.unlink(self.test_networks_file.name)
    
    def test_is_local_network(self):
        """Test is_local_network function correctly identifies private networks"""
        # Private networks should return True
        private_network1 = ipaddress.ip_network('192.168.1.0/24')
        private_network2 = ipaddress.ip_network('10.0.0.0/8')
        private_network3 = ipaddress.ip_network('172.16.0.0/12')
        
        # Public network should return False
        public_network = ipaddress.ip_network('8.8.8.0/24')
        
        self.assertTrue(is_local_network(private_network1))
        self.assertTrue(is_local_network(private_network2))
        self.assertTrue(is_local_network(private_network3))
        self.assertFalse(is_local_network(public_network))
    
    def test_process_input_csv(self):
        """Test process_input_csv function correctly processes CSV file"""
        networks, postal_codes = process_input_csv(self.test_csv_file.name)
        
        # Should have one public network
        self.assertEqual(len(networks), 1)
        self.assertEqual(networks[0], '8.8.8.0/24')
        
        # Postal code mapping should be correct
        self.assertEqual(postal_codes['8.8.8.0/24'], '98765')
    
    @patch('subprocess.run')
    def test_get_zmap_scan_results(self, mock_run):
        """Test get_zmap_scan_results function correctly handles ZMap output"""
        # Mock the subprocess.run result
        mock_process = MagicMock()
        mock_process.stdout = "8.8.8.1\n8.8.8.3\n"
        mock_run.return_value = mock_process
        
        # Create a temporary networks file
        networks_file = tempfile.NamedTemporaryFile(delete=False, suffix='.txt')
        with open(networks_file.name, 'w') as f:
            f.write('8.8.8.0/24\n')
        
        try:
            # Call the function
            result = get_zmap_scan_results(networks_file.name)
            
            # Check the result
            self.assertEqual(result, {'8.8.8.1', '8.8.8.3'})
            
            # Verify subprocess.run was called with correct arguments
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            self.assertEqual(args[0], 'zmap')
            self.assertEqual(args[2], '80')  # port
            self.assertEqual(args[4], '10M')  # bandwidth
        finally:
            os.unlink(networks_file.name)
    
    def test_calculate_availability(self):
        """Test calculate_availability function correctly calculates statistics"""
        networks = ['8.8.8.0/24']
        postal_codes = {'8.8.8.0/24': '98765'}
        reachable_ips = {'8.8.8.1', '8.8.8.3'}
        
        # Redirect stdout to capture the output
        captured_output = StringIO()
        sys.stdout = captured_output
        
        try:
            result = calculate_availability(networks, postal_codes, reachable_ips)
            
            # Check the result dictionary
            self.assertEqual(list(result.keys()), ['98765'])
            self.assertEqual(result['98765'][0], 2)  # 2 reachable IPs
            self.assertEqual(result['98765'][1], 254)  # 254 total IPs in a /24 network
        finally:
            sys.stdout = sys.__stdout__
    
    def test_load_networks_data(self):
        """Test load_networks_data function correctly loads and filters data"""
        df = load_networks_data(self.test_networks_file.name)
        
        # Check the DataFrame
        self.assertEqual(len(df), 3)
        self.assertEqual(df['reachable'].sum(), 2)  # 2 reachable IPs
    
    def test_viz_calculate_availability(self):
        """Test calculate_availability function in visualization module"""
        df = pd.DataFrame({
            'postal_code': ['98765', '98765', '98765'],
            'reachable': [1, 0, 1]
        })
        
        result = viz_calculate_availability(df)
        
        # Check the result
        self.assertEqual(list(result.keys()), ['98765'])
        self.assertEqual(result['98765'][0], 2)  # 2 reachable
        self.assertEqual(result['98765'][1], 3)  # 3 total

if __name__ == '__main__':
    unittest.main()