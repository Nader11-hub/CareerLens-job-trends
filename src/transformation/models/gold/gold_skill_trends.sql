-- MySQL 8.0+ equivalent of jsonb_array_elements_text().
-- Uses JSON_TABLE to unnest the tags JSON array into rows.
with exploded as (
    select
        jt.skill,
        s.published_month
    from {{ ref('silver_jobs') }} s,
    JSON_TABLE(
        coalesce(s.tags, '[]'),
        '$[*]' COLUMNS (skill VARCHAR(120) PATH '$')
    ) jt
    where s.tags is not null and JSON_LENGTH(s.tags) > 0
)
select
    lower(skill) as skill,
    published_month,
    count(*) as job_count
from exploded
group by lower(skill), published_month
