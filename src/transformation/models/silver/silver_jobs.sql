with bronze_jobs as (
    select
        id as job_id,
        source,
        title,
        company_name,
        category,
        coalesce(tags, '[]'::json) as tags,
        publication_date,
        date(publication_date) as published_date,
        date_trunc('month', publication_date)::date as published_month,
        case
            when candidate_required_location is null or btrim(candidate_required_location) = '' then 'Unknown'
            when lower(candidate_required_location) like '%worldwide%' then 'Global'
            when lower(candidate_required_location) like '%global%' then 'Global'
            when position(',' in candidate_required_location) > 0
                then btrim(split_part(candidate_required_location, ',', array_length(string_to_array(candidate_required_location, ','), 1)))
            else btrim(candidate_required_location)
        end as country
    from {{ source('bronze', 'bronze_jobs') }}
)
select
    job_id,
    source,
    title,
    company_name,
    category,
    title as role,
    country,
    tags,
    publication_date,
    published_date,
    published_month,
    null::float as salary_min,
    null::float as salary_max,
    null::varchar(10) as salary_currency,
    'Unspecified'::varchar(50) as seniority
from bronze_jobs

