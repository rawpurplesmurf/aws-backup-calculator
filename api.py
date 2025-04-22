from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import csv
from io import StringIO
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

app = FastAPI()

# Pricing map for warm and cold storage (per GB-month)
PRICE_MAP = {
    'EBS': {'warm': 0.05, 'cold': 0.0125},
    'EFS': {'warm': 0.05, 'cold': 0.01},
    'RDS': {'warm': 0.095, 'cold': None},  # Cold storage not supported for RDS
}

# Backup schedules
SCHEDULES = [
    {'name': 'intraday',    'interval': timedelta(hours=4),          'retention': timedelta(days=7),    'cold_after': None},
    {'name': 'daily',       'interval': timedelta(days=1),           'retention': timedelta(days=30),   'cold_after': timedelta(days=5)},
    {'name': 'weekly',      'interval': timedelta(weeks=1),          'retention': timedelta(days=90),   'cold_after': timedelta(days=5)},
    {'name': 'monthly_180','interval': relativedelta(months=1),      'retention': timedelta(days=180),  'cold_after': timedelta(days=5)},
    {'name': 'monthly_365','interval': relativedelta(months=1),      'retention': timedelta(days=365),  'cold_after': timedelta(days=5)},
    {'name': 'yearly',      'interval': relativedelta(years=1),       'retention': timedelta(days=365*5),'cold_after': timedelta(days=5)},
]

class Resource(BaseModel):
    type: str
    size_gb: float
    job: Optional[str] = None  # Name of the backup schedule to apply

class MonthlyCostItem(BaseModel):
    month: int
    cost: float
    breakdown: dict

class CostResponse(BaseModel):
    resource: Resource
    monthly_costs: List[MonthlyCostItem]


def calculate_monthly_costs(resource_type: str, size_gb: float, job_name: Optional[str] = None):
    print(f"\nCalculating costs for {resource_type} ({size_gb}GB) with {job_name} schedule...")
    
    if resource_type not in PRICE_MAP:
        raise ValueError(f"Unsupported resource type: {resource_type}")
    warm_price = PRICE_MAP[resource_type]['warm']
    cold_price = PRICE_MAP[resource_type]['cold']

    # Filter schedules if a specific job is requested
    schedules_to_use = [sched for sched in SCHEDULES if job_name is None or sched['name'] == job_name]
    if job_name and not schedules_to_use:
        raise ValueError(f"Unknown backup job: {job_name}")

    start_date = datetime.utcnow().date()
    results = []

    # Pre-calculate costs for different month lengths (28, 30, 31 days)
    month_length_costs = {}
    for days in [28, 30, 31]:
        month_length_costs[days] = {}
        for sched in schedules_to_use:
            if sched['retention'].days >= 31:  # Skip optimization for retention >= 31 days
                continue
                
            sched_cost = 0.0
            rp_time = start_date
            backup_points = 0
            
            # Calculate number of backup points in this month length
            while rp_time < start_date + timedelta(days=days):
                backup_points += 1
                # Calculate warm days
                warm_end = min(
                    rp_time + (sched['cold_after'] or sched['retention']),
                    rp_time + sched['retention'],
                    start_date + timedelta(days=days)
                )
                warm_days = max((warm_end - rp_time).days, 0)

                # Calculate cold days
                cold_days = 0
                if sched['cold_after'] and cold_price:
                    cold_start = rp_time + sched['cold_after']
                    if cold_start < start_date + timedelta(days=days):
                        cold_end = min(rp_time + sched['retention'], start_date + timedelta(days=days))
                        cold_days = max((cold_end - cold_start).days, 0)

                # Add cost for this recovery point
                sched_cost += size_gb * (warm_days / days) * warm_price
                if cold_price:
                    sched_cost += size_gb * (cold_days / days) * cold_price

                rp_time += sched['interval']

            month_length_costs[days][sched['name']] = round(sched_cost, 6)

    # Simulate each of the next 12 months
    for month_index in range(1, 13):
        print(f"\nProcessing month {month_index}/12...")
        month_start = start_date + relativedelta(months=month_index-1)
        month_end = month_start + relativedelta(months=1)
        days_in_month = (month_end - month_start).days

        month_cost = 0.0
        breakdown = {}

        for sched in schedules_to_use:
            print(f"  Processing {sched['name']} schedule...")
            
            if sched['retention'].days < 31 and days_in_month in month_length_costs:
                # Use pre-calculated cost for this month length
                sched_cost = month_length_costs[days_in_month].get(sched['name'], 0.0)
            else:
                # Calculate cost normally for longer retention periods
                sched_cost = 0.0
                rp_time = start_date
                backup_points = 0
                
                # Move to first recovery point in or after month_start
                while rp_time < month_start:
                    rp_time += sched['interval']
                
                # Iterate recovery points within the month
                while rp_time < month_end:
                    backup_points += 1
                    # Calculate warm days
                    warm_end = min(
                        rp_time + (sched['cold_after'] or sched['retention']),
                        rp_time + sched['retention'],
                        month_end
                    )
                    warm_days = max((warm_end - max(rp_time, month_start)).days, 0)

                    # Calculate cold days
                    cold_days = 0
                    if sched['cold_after'] and cold_price:
                        cold_start = rp_time + sched['cold_after']
                        if cold_start < month_end:
                            cold_end = min(rp_time + sched['retention'], month_end)
                            cold_days = max((cold_end - max(cold_start, month_start)).days, 0)

                    # Add cost for this recovery point
                    sched_cost += size_gb * (warm_days / days_in_month) * warm_price
                    if cold_price:
                        sched_cost += size_gb * (cold_days / days_in_month) * cold_price

                    rp_time += sched['interval']

            print(f"    Processed {backup_points} backup points for {sched['name']}")
            breakdown[sched['name']] = round(sched_cost, 6)
            month_cost += sched_cost

        results.append(MonthlyCostItem(month=month_index, cost=round(month_cost, 6), breakdown=breakdown))
        print(f"  Month {month_index} total cost: ${round(month_cost, 2)}")

    print("\nCalculation complete!")
    return results


@app.post("/calculate", response_model=CostResponse)
async def calculate_cost_json(resource: Resource):
    try:
        costs = calculate_monthly_costs(resource.type, resource.size_gb, resource.job)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return CostResponse(resource=resource, monthly_costs=costs)


@app.post("/calculate_csv", response_model=List[CostResponse])
async def calculate_cost_csv(file: UploadFile = File(...)):
    print("Received request")  # Debug log
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
    
    print(f"Reading file: {file.filename}")  # Debug log
    content = await file.read()
    print("File read complete")  # Debug log
    
    decoded = content.decode('utf-8')
    print("File decoded")  # Debug log
    
    reader = csv.DictReader(StringIO(decoded))
    responses = []
    
    print("Processing CSV rows")  # Debug log
    for row in reader:
        rt = row.get('type')
        size = float(row.get('size_gb', 0))
        job = row.get('job') or None
        print(f"Processing row: type={rt}, size={size}, job={job}")  # Debug log
        
        try:
            costs = calculate_monthly_costs(rt, size, job)
            responses.append(CostResponse(resource=Resource(type=rt, size_gb=size, job=job), monthly_costs=costs))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    print("Processing complete")  # Debug log
    return responses

# To run: uvicorn app:app --reload
