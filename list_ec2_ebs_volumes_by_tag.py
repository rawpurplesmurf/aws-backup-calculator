#!/usr/bin/env python3

import boto3
import csv
import argparse

def get_ec2_volumes_by_tag(tag_key):
    ec2 = boto3.client('ec2')
    # find instances with the tag key
    paginator = ec2.get_paginator('describe_instances')
    filters = [{'Name': f'tag-key', 'Values': [tag_key]}]
    rows = []

    for page in paginator.paginate(Filters=filters):
        for inst in page['Reservations']:
            for i in inst['Instances']:
                # grab the tag value
                tag_value = next((
                    t['Value']
                    for t in i.get('Tags', [])
                    if t['Key'] == tag_key
                ), None)
                if not tag_value:
                    continue

                # for each block device mapping, pull the volume size
                for mapping in i.get('BlockDeviceMappings', []):
                    ebs = mapping.get('Ebs')
                    if not ebs or 'VolumeId' not in ebs:
                        continue

                    vol = ec2.describe_volumes(VolumeIds=[ebs['VolumeId']])['Volumes'][0]
                    size_gb = vol['Size']

                    rows.append({
                        'type':        'EBS',
                        'size_gb':     size_gb,
                        'ec2_tag_value': tag_value
                    })

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

    rows = get_ec2_volumes_by_tag(args.tag_key)

    with open(args.output, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['type','size_gb','ec2_tag_value'])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print(f"Wrote {len(rows)} rows to {args.output}")

if __name__ == '__main__':
    main()

