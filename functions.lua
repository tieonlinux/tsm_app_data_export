local original_select = _G["select"]

_G["datastack"] = {}

function LoadData(tag, ...)
    local select = original_select
    if tag ~= "AUCTIONDB_MARKET_DATA" then
        _G.datastack = nil
        return
    end
    local realm = select(1, ...)
    local data = select(2, ...)
    assert(data)
    data = load(data)
    assert(data)
    data = data()

    _G.datastack = data
    _G.datastack['realm'] = realm
    _G.datastack['tag'] = tag
    return
end

function select_hook(which, ...)
    if which == 2 then
        return {['LoadData']=LoadData}
    end
    return original_select(which, ...)
end

function pre_hook()
    select = select_hook
end

function post_hook( ... )
    select = original_select
end