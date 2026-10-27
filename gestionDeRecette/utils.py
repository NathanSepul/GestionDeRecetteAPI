import os
from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_save


def reorder(obj_to_move, siblings, new_position):
    """Place obj_to_move à new_position parmi siblings et renumérote noOrdre (0, 1, 2...)."""
    ordered = list(siblings.exclude(id=obj_to_move.id).order_by('noOrdre'))
    ordered.insert(min(new_position, len(ordered)), obj_to_move)

    for index, obj in enumerate(ordered):
        obj.noOrdre = index

    type(obj_to_move).objects.bulk_update(ordered, ['noOrdre'])
    return ordered


def _remove_file(path):
    if path and os.path.isfile(path):
        os.remove(path)


def register_image_cleanup(model, field_name):
    """
    Supprime du disque l'image d'un modèle quand elle est remplacée ou quand l'objet est supprimé.
    La suppression n'a lieu qu'après le commit : si l'enregistrement échoue, l'ancien fichier est conservé.
    """
    storage = model._meta.get_field(field_name).storage
    uid = f"{model._meta.label}.{field_name}"

    def remember_old_file(sender, instance, **kwargs):
        instance._old_image_path = None
        if not instance.pk:
            return

        old_name = sender.objects.filter(pk=instance.pk).values_list(field_name, flat=True).first()
        new_name = getattr(instance, field_name).name
        if old_name and old_name != new_name:
            instance._old_image_path = storage.path(old_name)

    def delete_replaced_file(sender, instance, **kwargs):
        path = getattr(instance, '_old_image_path', None)
        if path:
            transaction.on_commit(lambda: _remove_file(path))

    def delete_file(sender, instance, **kwargs):
        file = getattr(instance, field_name)
        if file:
            path = file.path
            transaction.on_commit(lambda: _remove_file(path))

    pre_save.connect(remember_old_file, sender=model, weak=False, dispatch_uid=f"{uid}.pre_save")
    post_save.connect(delete_replaced_file, sender=model, weak=False, dispatch_uid=f"{uid}.post_save")
    post_delete.connect(delete_file, sender=model, weak=False, dispatch_uid=f"{uid}.post_delete")
