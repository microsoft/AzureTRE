def get_installation_id(msg_body):
    """
    This is used to identify each bundle install within the porter state store.
    """
    return msg_body['id']
