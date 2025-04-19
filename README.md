# AWS Backup Calculator API

I needed this after coming across 39,000 ebs snapshots in an account, math is hard, especially with a lot of data, this is prety much all the work of AI, started with chatGPT and refined in cursor. 


A FastAPI-based calculator for estimating AWS backup costs across different storage types and backup schedules. This tool helps you estimate the costs of backing up your AWS resources (EBS, EFS, and RDS) with various backup schedules and retention policies.

## Features

- Calculate backup costs for multiple AWS storage types:
  - EBS (Elastic Block Storage)
  - EFS (Elastic File System)
  - RDS (Relational Database Service)
- Support for both warm and cold storage tiers
- Multiple backup schedule options:
  - Intraday (every 4 hours, 7-day retention)
  - Daily (30-day retention)
  - Weekly (90-day retention)
  - Monthly (180-day retention)
  - Monthly (365-day retention)
  - Yearly (5-year retention)
  - Frequent (every 2 hours, 3-day retention)
  - Biweekly (every 2 weeks, 120-day retention)
  - Semi-annual (every 6 months, 2-year retention)
- Cost breakdown by schedule
- Support for both single resource calculations and bulk CSV processing
- 12-month cost projection

## Current Pricing (per GB-month)

| Storage Type | Warm Storage | Cold Storage |
|-------------|--------------|--------------|
| EBS         | $0.05       | $0.0125      |
| EFS         | $0.05       | $0.01        |
| RDS         | $0.095      | N/A          |

## Configuration Parameters

### Storage Pricing Configuration

The `PRICE_MAP` dictionary defines the cost per GB-month for different storage types and tiers. This is crucial for accurate cost calculations and should be updated when AWS prices change.

```python
PRICE_MAP = {
    'EBS': {'warm': 0.05, 'cold': 0.0125},
    'EFS': {'warm': 0.05, 'cold': 0.01},
    'RDS': {'warm': 0.095, 'cold': None},  # Cold storage not supported for RDS
}
```

#### Price Map Structure
- Each storage type (EBS, EFS, RDS) has two possible storage tiers:
  - `warm`: Primary storage tier (higher cost, immediate access)
  - `cold`: Archive storage tier (lower cost, delayed access)
- Prices are in USD per GB-month
- `None` value indicates the tier is not supported (e.g., RDS cold storage)

#### Updating Prices
To update prices when AWS changes their pricing:
1. Find the new price per GB-month for the storage type
2. Update the corresponding value in the `PRICE_MAP`
3. Keep the structure and keys the same
4. Maintain the `None` value for unsupported features

### Backup Schedule Configuration

The `SCHEDULES` list defines different backup patterns and retention policies. Each schedule determines when backups are taken and how long they're kept.

```python
SCHEDULES = [
    {
        'name': 'intraday',
        'interval': timedelta(hours=4),
        'retention': timedelta(days=7),
        'cold_after': None
    },
    # ... other schedules
]
```

#### Schedule Parameters
Each schedule is a dictionary with four required parameters:

1. `name` (string):
   - Unique identifier for the schedule
   - Used in API requests and reporting
   - Should be descriptive and lowercase

2. `interval` (timedelta or relativedelta):
   - How frequently backups are taken
   - Use `timedelta` for hours/days/weeks
   - Use `relativedelta` for months/years
   - Examples:
     ```python
     timedelta(hours=4)    # Every 4 hours
     timedelta(days=1)     # Daily
     timedelta(weeks=1)    # Weekly
     relativedelta(months=1)  # Monthly
     relativedelta(years=1)   # Yearly
     ```

3. `retention` (timedelta):
   - How long backups are kept before deletion
   - Always use `timedelta`
   - Examples:
     ```python
     timedelta(days=7)     # One week
     timedelta(days=30)    # One month
     timedelta(days=365)   # One year
     ```

4. `cold_after` (timedelta or None):
   - When to transition to cold storage
   - Use `None` for no cold storage transition
   - Must be less than retention period
   - Typically 5 days for supported storage types

#### Current Schedule Definitions

| Schedule Name | Interval | Retention | Cold Storage Transition |
|--------------|----------|-----------|------------------------|
| intraday | 4 hours | 7 days | No transition |
| daily | 1 day | 30 days | After 5 days |
| weekly | 1 week | 90 days | After 5 days |
| monthly_180 | 1 month | 180 days | After 5 days |
| monthly_365 | 1 month | 365 days | After 5 days |
| yearly | 1 year | 5 years | After 5 days |

#### Adding New Schedules

To add a new schedule:
1. Create a new dictionary in the `SCHEDULES` list
2. Include all required parameters
3. Follow the existing naming convention
4. Ensure the cold_after period is less than retention
5. Use appropriate time classes for intervals

Example of adding a new schedule:
```python
{
    'name': 'quarterly',
    'interval': relativedelta(months=3),
    'retention': timedelta(days=365),
    'cold_after': timedelta(days=5)
}
```

#### Maintenance Considerations

When maintaining schedules:
1. Don't modify existing schedule names as they may be referenced in automated jobs
2. Ensure cold storage transitions are only enabled for supported storage types
3. Test new schedules with small storage sizes first
4. Consider the computational impact of short intervals (like intraday backups)
5. Keep retention periods aligned with compliance requirements
6. Document any custom schedules added for specific use cases

The calculation time will increase with:
- Shorter intervals (more backup points to calculate)
- Longer retention periods
- Larger storage sizes

## Installation

### Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd aws-backup-calculator
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### Running the API

Start the server with:
```bash
uvicorn api:app --reload
```

The API will be available at `http://127.0.0.1:8000`

For production deployment, remove the `--reload` flag and consider adding host and port parameters:
```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```

## API Endpoints

### 1. Calculate Single Resource Cost

**Endpoint:** `POST /calculate`

**Request Body:**
```json
{
    "type": "EBS",
    "size_gb": 100,
    "job": "daily"
}
```

- `type`: Storage type (EBS, EFS, or RDS)
- `size_gb`: Size in gigabytes
- `job`: Backup schedule name (optional)

### 2. Calculate Multiple Resources (CSV)

**Endpoint:** `POST /calculate_csv`

Upload a CSV file with the following headers:
- `type`: Storage type
- `size_gb`: Size in gigabytes
- `job`: Backup schedule (optional)

## Backup Schedules

| Schedule Name | Interval | Retention Period | Cold Transition |
|--------------|----------|------------------|-----------------|
| intraday     | 4 hours  | 7 days          | N/A            |
| daily        | 1 day    | 30 days         | After 5 days   |
| weekly       | 1 week   | 90 days         | After 5 days   |
| monthly_180  | 1 month  | 180 days        | After 5 days   |
| monthly_365  | 1 month  | 365 days        | After 5 days   |
| yearly       | 1 year   | 5 years         | After 5 days   |
| frequent     | 2 hours  | 3 days          | N/A            |
| biweekly     | 2 weeks  | 120 days        | After 10 days  |
| semi_annual  | 6 months | 2 years         | After 30 days  |

## Example Usage

### Using curl

#### Single Resource Calculation
```bash
# Single resource calculation
curl -X POST "http://127.0.0.1:8000/calculate" \
-H "Content-Type: application/json" \
-d '{"type": "EBS", "size_gb": 100, "job": "daily"}'
```

#### CSV Bulk Calculation
First, create a file named `backup_resources.csv` with the following content:

```csv
type,size_gb,job
EBS,100,weekly
RDS,500,intraday
EFS,10000,monthly_180
```

This sample file includes:
1. A 100GB EBS volume with weekly backups (90-day retention)
2. A 500GB RDS instance with backups every 4 hours (7-day retention)
3. A 10000GB EFS volume with monthly backups (180-day retention)

Then run the calculation:
```bash
curl -X POST "http://127.0.0.1:8000/calculate_csv" \
-F "file=@backup_resources.csv"
```

#### Sample Response
The API will return a JSON response with cost projections for each resource. Here's a simplified example of what the response structure looks like:

```json
[
  {
    "resource": {
      "type": "EBS",
      "size_gb": 100,
      "job": "weekly"
    },
    "monthly_costs": [
      {
        "month": 1,
        "cost": 2.75,
        "breakdown": {
          "weekly": 2.75
        }
      },
      // ... remaining months
    ]
  },
  {
    "resource": {
      "type": "RDS",
      "size_gb": 500,
      "job": "intraday"
    },
    "monthly_costs": [
      {
        "month": 1,
        "cost": 47.5,
        "breakdown": {
          "intraday": 47.5
        }
      },
      // ... remaining months
    ]
  },
  {
    "resource": {
      "type": "EFS",
      "size_gb": 10000,
      "job": "monthly_180"
    },
    "monthly_costs": [
      {
        "month": 1,
        "cost": 450.0,
        "breakdown": {
          "monthly_180": 450.0
        }
      },
      // ... remaining months
    ]
  }
]
```

### Understanding the Results

For each resource in the CSV file, the calculator considers:

1. **EBS Volume (100GB, weekly)**
   - Weekly snapshots with 90-day retention
   - Transitions to cold storage after 5 days
   - Uses both warm ($0.05/GB-month) and cold ($0.0125/GB-month) storage

2. **RDS Instance (500GB, intraday)**
   - Backups every 4 hours with 7-day retention
   - No cold storage support
   - Uses only warm storage ($0.095/GB-month)

3. **EFS Volume (10000GB, monthly_180)**
   - Monthly backups with 180-day retention
   - Transitions to cold storage after 5 days
   - Uses both warm ($0.05/GB-month) and cold ($0.01/GB-month) storage

The response includes a 12-month projection for each resource, with costs broken down by backup schedule and storage tier.

## API Documentation

The API provides automatic interactive documentation:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## Response Format

The API returns a JSON response with monthly cost projections for the next 12 months:

```json
{
  "resource": {
    "type": "EBS",
    "size_gb": 100,
    "job": "daily"
  },
  "monthly_costs": [
    {
      "month": 1,
      "cost": 5.25,
      "breakdown": {
        "daily": 5.25
      }
    },
    // ... remaining months
  ]
}
```