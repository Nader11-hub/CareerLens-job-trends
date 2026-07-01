with bronze_jobs as (
    select
        id as job_id,
        source,
        title,
        company_name,
        category,
        coalesce(tags, JSON_ARRAY()) as tags,
        publication_date,
        date(publication_date) as published_date,
        -- MySQL equivalent of date_trunc('month', ...)::date
        date(date_format(publication_date, '%Y-%m-01')) as published_month,
        case
            when candidate_required_location is null or trim(candidate_required_location) = '' then 'Unknown'
            when lower(candidate_required_location) like '%worldwide%' then 'Global'
            when lower(candidate_required_location) like '%global%' then 'Global'
            -- MySQL: LOCATE replaces position(), SUBSTRING_INDEX replaces split_part()
            when locate(',', candidate_required_location) > 0
                then trim(substring_index(candidate_required_location, ',', -1))
            else trim(candidate_required_location)
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
    null as salary_min,
    null as salary_max,
    null as salary_currency,
    'Unspecified' as seniority
from bronze_jobs
