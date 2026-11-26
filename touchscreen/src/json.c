#include "screen.h"
#include <stdlib.h>
#include <string.h>
/* Patches replace whole top-level sections. Null is a value, not a deletion;
 * explicit removals keep reconnects and cleared data unambiguous. */
const cJSON *json_update_value(const cJSON *previous, const cJSON *update, const char *path) {
    if (!jbool(update, "_screen_patch", false))
        return jget(update, path);
    size_t length = strcspn(path, ".");
    const cJSON *item;
    cJSON_ArrayForEach(item, jget(update, "remove"))
        if (cJSON_IsString(item) && strlen(item->valuestring) == length &&
            !strncmp(path, item->valuestring, length))
            return NULL;
    const cJSON *changes = jget(update, "set");
    cJSON_ArrayForEach(item, changes)
        if (item->string && strlen(item->string) == length && !strncmp(path, item->string, length))
            return jget(changes, path);
    return jget(previous, path);
}

cJSON *json_update(cJSON *previous, cJSON *update) {
    if (!jbool(update, "_screen_patch", false)) {
        cJSON_Delete(previous);
        return update;
    }
    cJSON *changes = jget(update, "set"), *item;
    while (changes && changes->child) {
        item = cJSON_DetachItemViaPointer(changes, changes->child);
        cJSON *existing = cJSON_GetObjectItemCaseSensitive(previous, item->string);
        if (existing)
            cJSON_ReplaceItemViaPointer(previous, existing, item);
        else {
            char *key = strdup(item->string);
            if (key) {
                cJSON_AddItemToObject(previous, key, item);
                free(key);
            } else
                cJSON_Delete(item);
        }
    }
    cJSON_ArrayForEach(item, jget(update, "remove"))
        if (cJSON_IsString(item))
            cJSON_DeleteItemFromObjectCaseSensitive(previous, item->valuestring);
    cJSON_Delete(update);
    return previous;
}

/* Fast path for stable snapshot key order; no copied trees or JSON strings.
 * A producer may reorder object keys, so retain order-independent equality as
 * a fallback. Arrays remain ordered, and missing values differ from null. */
bool json_equal(const cJSON *left, const cJSON *right) {
    if (left == right)
        return true;
    if (!left || !right)
        return false;
    bool object = cJSON_IsObject(left) && cJSON_IsObject(right);
    bool array = cJSON_IsArray(left) && cJSON_IsArray(right);
    if (!object && !array)
        return cJSON_Compare(left, right, true);
    const cJSON *a = left->child, *b = right->child;
    for (; a && b; a = a->next, b = b->next) {
        if (object && strcmp(a->string, b->string))
            return cJSON_Compare(left, right, true);
        if (!json_equal(a, b))
            return false;
    }
    return !a && !b;
}

cJSON *jget(const cJSON *object, const char *path) {
    char key[160];
    const char *p = path;
    while (object && *p) {
        const char *end = strchr(p, '.');
        size_t n = end ? (size_t)(end - p) : strlen(p);
        if (n >= sizeof(key))
            return NULL;
        memcpy(key, p, n);
        key[n] = 0;
        object = cJSON_IsArray(object) ? cJSON_GetArrayItem(object, atoi(key))
                                       : cJSON_GetObjectItemCaseSensitive(object, key);
        p = end ? end + 1 : p + n;
    }
    return (cJSON *)object;
}
const char *jstr(const cJSON *o, const char *p, const char *fallback) {
    cJSON *v = jget(o, p);
    return cJSON_IsString(v) ? v->valuestring : fallback;
}
double jnum(const cJSON *o, const char *p, double fallback) {
    cJSON *v = jget(o, p);
    return cJSON_IsNumber(v) ? v->valuedouble : fallback;
}
bool jbool(const cJSON *o, const char *p, bool fallback) {
    cJSON *v = jget(o, p);
    if (cJSON_IsBool(v))
        return cJSON_IsTrue(v);
    return cJSON_IsNumber(v) ? v->valuedouble != 0 : fallback;
}
cJSON *J(const char *p) {
    return jget(app.data, p);
}
const char *S(const char *p) {
    return jstr(app.data, p, "");
}
double N(const char *p) {
    return jnum(app.data, p, 0);
}
bool B(const char *p) {
    return jbool(app.data, p, false);
}
char *request_json(const char *action, const char *key, const char *value) {
    cJSON *o = cJSON_CreateObject();
    cJSON_AddStringToObject(o, "action", action);
    if (key)
        cJSON_AddStringToObject(o, key, value);
    char *s = cJSON_PrintUnformatted(o);
    cJSON_Delete(o);
    return s;
}
