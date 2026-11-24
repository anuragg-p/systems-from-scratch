-- find.lua: go to a line, and find as you type, on keys of their own.
--
-- Ctrl-O asks for a line number and goes there. Ctrl-N starts a find, as
-- the core's Ctrl-F does it: while it lasts a KeyPress function takes every
-- key. A character adds to the query, and the search starts again from the
-- top; Backspace takes one off; Down or Right go to the next match, Up or
-- Left to the one before, round the end of the file; Enter stays there;
-- Escape puts the cursor and the view back where they were. The match's
-- row is put at the top of the screen, and the match drawn in blue.
--
-- Load it after colour.lua (its blue must be drawn last) and before vi.lua
-- (a find must take its keys before vi's normal mode does).

local api = kilo.api
local ns = api.create_namespace('find')
local find = {active = false}

local function say()
  api.message('Search: ' .. find.query .. ' (Use ESC/Arrows/Enter)')
end

-- The first row after from, going by dir (1 or -1) and round the end, that
-- holds the query; its row and the byte where the query starts.
local function search(from, dir)
  local count = api.line_count()
  local lines = api.get_lines(0, count)
  local row = from
  for _ = 1, count do
    row = row + dir
    if row < 0 then row = count - 1 elseif row >= count then row = 0 end
    local col = lines[row + 1]:find(find.query, 1, true)
    if col then return row, col - 1 end
  end
end

-- Draw the match, while a find lasts. Also after every change and move:
-- another plugin that draws again then (colour.lua) would cover it, and
-- later highlights are drawn over earlier ones, so load this one after.
local function mark()
  api.clear_namespace(ns)
  local m = find.match
  if find.active and m and m[1] < api.line_count() then
    api.add_highlight(ns, m[1], m[2], m[2] + #find.query, 'blue')
  end
end
api.create_autocmd('TextChanged', mark)
api.create_autocmd('CursorMoved', mark)

-- Go to the next match by dir, from the last one (or from the top).
local function go(dir)
  find.match = nil
  if find.query ~= '' then
    local row, col = search(find.last or -1, dir)
    if row then
      find.last, find.match = row, {row, col}
      api.set_view({row, 0})
      api.set_cursor({row, col})
    end
  end
  mark()
end

api.create_autocmd('KeyPress', function(key)
  if not find.active then return false end
  if key == '<Esc>' or key == '<Enter>' then
    find.active, find.match = false, nil
    api.clear_namespace(ns)
    if key == '<Esc>' then
      api.set_cursor(find.cursor)
      api.set_view(find.view)
    end
    api.message('')
    return true
  elseif key == '<Down>' or key == '<Right>' then
    go(1)
  elseif key == '<Up>' or key == '<Left>' then
    go(-1)
  elseif key == '<BS>' or key == '<Del>' or key == '<C-h>' then
    find.query, find.last = find.query:sub(1, -2), nil
    go(1)
  elseif #key == 1 or key == '<Space>' then
    find.query, find.last = find.query .. (key == '<Space>' and ' ' or key), nil
    go(1)
  end
  say()
  return true
end)

api.set_keymap('<C-n>', function()
  find.active, find.query, find.last, find.match = true, '', nil, nil
  find.cursor, find.view = api.get_cursor(), api.get_view()
  say()
end)

api.set_keymap('<C-o>', function()
  local s = api.input('Go to line: ')
  local n = tonumber(s or '')
  if n and n >= 1 and n <= api.line_count() then
    api.set_cursor({math.floor(n) - 1, 0})
  elseif s then
    api.message('no line ' .. s)
  end
end)

return find
