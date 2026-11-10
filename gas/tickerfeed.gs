/**
 * tickerfeed: GOOGLEFINANCE-like custom function backed by the tickerfeed API.
 *
 * Script properties (Extensions → Apps Script → Project settings → Script properties):
 *   TICKERFEED_URL      e.g. http://1.2.3.4:8742
 *   TICKERFEED_API_KEY  same as api_key in server .env
 */

var ATTRIBUTES = ['price', 'currency', 'name'];
var CLIENT_CACHE_SECONDS = 5 * 60;
var CACHE_PREFIX = 'tickerfeed:';

/**
 * Returns a quote attribute, like GOOGLEFINANCE.
 *
 * @param {string|Array<Array<string>>} symbols "LSE:VUSA", "NYSE:KO" or a range of them.
 * @param {string} attribute price (default), currency, name.
 * @param {boolean} gbp convert pence-quoted LSE instruments to GBP, default FALSE.
 * @return attribute value(s), same shape as symbols.
 * @customfunction
 */
function TICKERFEED(symbols, attribute, gbp) {
    attribute = (attribute || 'price').toString().toLowerCase();
    if (ATTRIBUTES.indexOf(attribute) === -1) {
        throw new Error('unknown attribute ' + attribute + ', expected one of ' + ATTRIBUTES.join(', '));
    }
    gbp = gbp === true;

    if (!Array.isArray(symbols)) {
        var single = fetchResults_([symbols.toString().trim()], gbp)[symbols.toString().trim()];
        if (single.error) {
            throw new Error(single.error);
        }
        return attributeValue_(single.quote, attribute);
    }

    var queries = [];
    symbols.forEach(function (row) {
        row.forEach(function (cell) {
            var query = cell.toString().trim();
            if (query && queries.indexOf(query) === -1) {
                queries.push(query);
            }
        });
    });
    var results = fetchResults_(queries, gbp);

    return symbols.map(function (row) {
        return row.map(function (cell) {
            var query = cell.toString().trim();
            if (!query) {
                return '';
            }
            var result = results[query];
            return result.error ? '#' + result.error : attributeValue_(result.quote, attribute);
        });
    });
}

function attributeValue_(quote, attribute) {
    var value = quote[attribute];
    if (value === null || value === undefined) {
        return '';
    }
    return value;
}

/** Map query → {quote, error}; serves from CacheService, fetches the rest in one request. */
function fetchResults_(queries, gbp) {
    var cache = CacheService.getScriptCache();
    var keys = queries.map(function (query) {
        return CACHE_PREFIX + (gbp ? 'gbp:' : '') + query;
    });
    var cached = cache.getAll(keys);

    var results = {};
    var missing = [];
    queries.forEach(function (query, i) {
        if (cached[keys[i]]) {
            results[query] = JSON.parse(cached[keys[i]]);
        } else {
            missing.push(query);
        }
    });
    if (!missing.length) {
        return results;
    }

    var props = PropertiesService.getScriptProperties();
    var url = props.getProperty('TICKERFEED_URL') + '/v1/quotes?symbols=' + encodeURIComponent(missing.join(',')) + '&gbp=' + gbp;
    var response = UrlFetchApp.fetch(url, {
        headers: {'X-Api-Key': props.getProperty('TICKERFEED_API_KEY')},
        muteHttpExceptions: true,
    });
    if (response.getResponseCode() !== 200) {
        throw new Error('tickerfeed responded ' + response.getResponseCode() + ': ' + response.getContentText().slice(0, 200));
    }

    var toCache = {};
    JSON.parse(response.getContentText()).results.forEach(function (result) {
        results[result.query] = result;
        // ошибки провайдера и stale не кешируем — пусть следующий пересчёт попробует снова
        if (result.quote && !result.stale) {
            toCache[CACHE_PREFIX + (gbp ? 'gbp:' : '') + result.query] = JSON.stringify(result);
        }
    });
    cache.putAll(toCache, CLIENT_CACHE_SECONDS);
    return results;
}
