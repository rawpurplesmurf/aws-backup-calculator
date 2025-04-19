# AWS Backup Calculator API

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

## Security Considerations

This API doesn't include authentication or rate limiting. For production deployment, consider:
- Adding authentication
- Implementing rate limiting
- Using HTTPS
- Setting up proper firewall rules
- Implementing input validation and sanitization

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]
