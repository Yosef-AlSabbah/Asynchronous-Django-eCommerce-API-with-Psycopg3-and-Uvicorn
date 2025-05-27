from celery import shared_task


@shared_task
def log_action_async(user_id, table, object_id, action, changes=None):
    """
    Celery task to log model changes asynchronously
    """
    from .models import ActionLog

    ActionLog.objects.create(
        user_id=user_id,
        table=table,
        object_id=object_id,
        action=action,
        changes=changes,
    )