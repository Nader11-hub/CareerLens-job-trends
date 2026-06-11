with exploded as (
    select
        jsonb_array_elements_text(tags::jsonb) as skill,
        published_month
    from {{ ref('silver_jobs') }}
)
select
    lower(skill) as skill,
    published_month,
    count(*) as job_count
from exploded
group by 1, 2
