-- vi.lua: a normal mode and an insert mode for kilo, as vi has them.
--
-- Every key reaches the KeyPress functions before the editor sees it. In
-- normal mode this one takes the keys it knows and does their work with
-- the API; a printable key it does not know does nothing; a named key
-- (an arrow, Ctrl-S, ...) is given back to the editor. In insert mode it
-- gives every key back, but Escape. The mode is shown in the status bar.

local api = kilo.api
local vi = {mode = 'normal'}
local pending = nil                     -- 'd' after the first d of dd

local function show()
  api.set_statusline('-- ' .. vi.mode:upper() .. ' -- ' .. api.get_name())
end

local function line(row)                -- the row's text; '' past the last
  if row >= api.line_count() then return '' end
  return api.get_lines(row, row + 1)[1]
end

local function cursor()
  local c = api.get_cursor()
  return c[1], c[2]
end

local function go(row, col)             -- normal mode sits on a character
  local last = math.max(#line(row) - 1, 0)
  api.set_cursor({row, math.max(math.min(col, last), 0)})
end

local normal = {}
normal['h'] = function() local r, c = cursor() go(r, c - 1) end
normal['l'] = function() local r, c = cursor() go(r, c + 1) end
normal['j'] = function()
  local r, c = cursor()
  if r + 1 < api.line_count() then go(r + 1, c) end
end
normal['k'] = function() local r, c = cursor() if r > 0 then go(r - 1, c) end end
normal['0'] = function() local r = cursor() go(r, 0) end
normal['$'] = function() local r = cursor() go(r, #line(r)) end
normal['i'] = function() vi.mode = 'insert' end
normal['a'] = function()
  local r, c = cursor()
  if #line(r) > 0 then api.set_cursor({r, c + 1}) end
  vi.mode = 'insert'
end
normal['o'] = function()
  local r = cursor()
  api.set_lines(r + 1, r + 1, {''})
  api.set_cursor({r + 1, 0})
  vi.mode = 'insert'
end
normal['x'] = function()
  local r, c = cursor()
  local s = line(r)
  if #s == 0 then return end
  api.set_lines(r, r + 1, {s:sub(1, c) .. s:sub(c + 2)})
  go(r, c)
end
normal['d'] = function() pending = 'd' end
normal['<Enter>'] = normal['j']
normal['<BS>'] = normal['h']

api.create_autocmd('KeyPress', function(key)
  if vi.mode == 'insert' then
    if key ~= '<Esc>' then return false end
    vi.mode = 'normal'
    local r, c = cursor()
    go(r, c - 1)                        -- vi steps back onto the last character typed
  elseif pending then
    pending = nil
    local r = cursor()
    if key == 'd' and r < api.line_count() then
      api.set_lines(r, r + 1, {})
      go(cursor())
    end
  elseif normal[key] then
    normal[key]()
  elseif #key > 1 and key:sub(1, 1) == '<' then
    return false                        -- a named key: the editor's own
  end
  show()
  return true
end)

api.create_autocmd('BufReadPost', show)    -- another file: its name in the bar
show()
return vi
