#!/usr/bin/env python3

import boto3
import argparse
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_volume_snapshots(volume_id, region=None):
    """
    Get all snapshots for a given EBS volume ID.
    
    Args:
        volume_id (str): The ID of the EBS volume
        region (str, optional): AWS region name
    
    Returns:
        list: List of snapshots with their details
    """
    logger.info(f"Connecting to EC2 in region: {region or 'default'}")
    ec2 = boto3.client('ec2', region_name=region)
    
    try:
        # First verify the volume exists
        logger.info(f"Verifying volume {volume_id} exists")
        volume = ec2.describe_volumes(VolumeIds=[volume_id])['Volumes'][0]
        logger.info(f"Found volume {volume_id} with size {volume['Size']}GB")
        
        # Get all snapshots for this volume
        logger.info(f"Searching for snapshots of volume {volume_id}")
        paginator = ec2.get_paginator('describe_snapshots')
        snapshots = []
        
        for page in paginator.paginate(Filters=[{'Name': 'volume-id', 'Values': [volume_id]}]):
            for snapshot in page['Snapshots']:
                # Convert start time to readable format
                start_time = snapshot['StartTime']
                if isinstance(start_time, datetime):
                    start_time_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    start_time_str = str(start_time)
                
                snap_info = {
                    'SnapshotId': snapshot['SnapshotId'],
                    'StartTime': start_time_str,
                    'State': snapshot['State'],
                    'Progress': snapshot['Progress'],
                    'VolumeSize': snapshot['VolumeSize'],
                    'Description': snapshot.get('Description', '')
                }
                snapshots.append(snap_info)
                logger.info(f"Found snapshot {snapshot['SnapshotId']} created at {start_time_str}")
        
        logger.info(f"Found {len(snapshots)} snapshots for volume {volume_id}")
        return snapshots
        
    except Exception as e:
        logger.error(f"Error processing volume {volume_id}: {str(e)}")
        raise

def main():
    parser = argparse.ArgumentParser(
        description='List all snapshots for a given EBS volume'
    )
    parser.add_argument(
        'volume_id',
        help='The ID of the EBS volume'
    )
    parser.add_argument(
        '--region', '-r',
        help='AWS region (will use default if unset)',
        default=None
    )
    parser.add_argument(
        '--output', '-o',
        help='Output format (json or table)',
        choices=['json', 'table'],
        default='table'
    )
    args = parser.parse_args()

    try:
        snapshots = get_volume_snapshots(args.volume_id, args.region)
        
        if args.output == 'json':
            import json
            print(json.dumps(snapshots, indent=2))
        else:
            # Print as a table
            if not snapshots:
                print("No snapshots found for this volume.")
                return
                
            # Print header
            print("\nSnapshot Details:")
            print("-" * 100)
            print(f"{'Snapshot ID':<20} {'Created':<20} {'State':<10} {'Progress':<10} {'Size (GB)':<10} {'Description'}")
            print("-" * 100)
            
            # Print each snapshot
            for snap in snapshots:
                print(f"{snap['SnapshotId']:<20} {snap['StartTime']:<20} {snap['State']:<10} "
                      f"{snap['Progress']:<10} {snap['VolumeSize']:<10} {snap['Description']}")
            
            print("-" * 100)
            print(f"Total snapshots: {len(snapshots)}")
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return 1

if __name__ == '__main__':
    main() 