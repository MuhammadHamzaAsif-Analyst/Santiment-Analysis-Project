SELECT * FROM social_media_db.posts;

SELECT sum(likes_count) from social_media_db.posts;

select platform, sum(likes_count)
from social_media_db.posts
group by platform;

select post_id, (likes_count + shares_count + comments_count) as engagement
from social_media_db.posts
order by engagement desc
limit 10;




select sentiment_label, avg (likes_count + shares_count + comments_count)
from social_media_db.posts
group by sentiment_label;
