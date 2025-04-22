#!/usr/bin/env python3

import boto3
import csv
import argparse

def get_ec2_volumes_by_tag(tag_key):
    ec2 = boto3.client('ec2')
    logger.info(f"Searching for EC2 instances with tag key: {tag_key}")
    
    # find instances with the tag key
    paginator = ec2.get_paginator('describe_instances')
    filters = [{'Name': f'tag-key', 'Values': [tag_key]}]
    rows = []

    for page in paginator.paginate(Filters=filters):
        for inst in page['Reservations']:
            for i in inst['Instances']:
                instance_id = i['InstanceId']
                logger.info(f"Processing instance: {instance_id}")
                
                # grab the tag value
                tag_value = next((
                    t['Value']
                    for t in i.get('Tags', [])
                    if t['Key'] == tag_key
                ), None)
                if not tag_value:
                    logger.warning(f"Instance {instance_id} has tag key {tag_key} but no value")
                    continue

                logger.info(f"Found tag value '{tag_value}' for instance {instance_id}")

                # for each block device mapping, pull the volume size
                for mapping in i.get('BlockDeviceMappings', []):
                    ebs = mapping.get('Ebs')
                    if not ebs or 'VolumeId' not in ebs:
                        logger.warning(f"No EBS volume found for device {mapping.get('DeviceName')} on instance {instance_id}")
                        continue

                    volume_id = ebs['VolumeId']
                    logger.info(f"Processing volume {volume_id} for instance {instance_id}")

                    try:
                        vol = ec2.describe_volumes(VolumeIds=[volume_id])['Volumes'][0]
                        size_gb = vol['Size']
                        logger.info(f"Volume {volume_id} size: {size_gb}GB")

                        rows.append({
                            'type':        'EBS',
                            'size_gb':     size_gb,
                            'ec2_tag_value': tag_value
                        })
                    except Exception as e:
                        logger.error(f"Error describing volume {volume_id}: {e}")

    logger.info(f"Found {len(rows)} EBS volumes across all instances")
    return rows

def main():
    parser = argparse.ArgumentParser(
        description='List all EBS volumes attached to EC2 instances with a given tag'
    )
    parser.add_argument(
        '--tag-key', default='cpm_backup',
        help='EC2 tag key to filter on (default: cpm_backup)'
    )
    parser.add_argument(
        '--output', default='ebs_volumes.csv',
        help='Output CSV file path'
    )
    args = parser.parse_args()

    logger.info(f"Starting EBS volume discovery with tag key: {args.tag_key}")
    rows = get_ec2_volumes_by_tag(args.tag_key)

    logger.info(f"Writing {len(rows)} rows to {args.output}")
    with open(args.output, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['type','size_gb','ec2_tag_value'])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    logger.info(f"Successfully wrote {len(rows)} rows to {args.output}")

if __name__ == '__main__':
    main()

