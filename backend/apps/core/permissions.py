def is_admin(user):

    return (
        user.is_authenticated
        and
        user.role
        and
        user.role.name == "Admin"
    )

