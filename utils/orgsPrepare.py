from services.mo_alias_service import mo_alias_service


def prepareOrgsList(medic_orgs):
    organizations_list = []
    organizations_list_ttl = []

    if medic_orgs is None:
        return None, None

    for i, org in enumerate(medic_orgs, 1):
        oid = org['oid'] if org['oid'] else None
        name = org['name'] if org['name'] else None
        address = org['name'] if org['address'] else None

        if oid is None:
            continue

        alias_object = mo_alias_service.get_mo_info_by_oid(oid)
        if alias_object:
            short_name = alias_object['short_name_text'] if alias_object['short_name_ttl'] else None
            short_name_ttl = alias_object['short_name_ttl'] if alias_object['short_name_ttl'] else None

            org_info = f"{i}. {short_name}"
            org_info_ttl = f"{i}. {short_name_ttl if short_name_ttl else short_name}"
        else:
            org_info = f"{i}. {name}, {address}"
            org_info_ttl = org_info

        organizations_list.append(org_info)
        organizations_list_ttl.append(org_info_ttl)

    # Объединяем все организации в одну строку
    organizations_text = "\n".join(organizations_list)
    organizations_list_ttl = "\n - ".join(organizations_list_ttl)
    return organizations_text, organizations_list_ttl
