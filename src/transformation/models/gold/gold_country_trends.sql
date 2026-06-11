select
    country,
    published_month,
    count(*) as job_count
from {{ ref('silver_jobs') }}
group by 1, 2
