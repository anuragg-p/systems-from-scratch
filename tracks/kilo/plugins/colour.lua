-- colour.lua: colours for C and Lua files, as module 06 gives C: numbers,
-- strings, comments on one line and over many, keywords and types.
--
-- They are drawn as highlights, in a namespace of this plugin's, over the
-- rows the screen shows, and drawn again whenever a file is read, the text
-- changes or the cursor moves (the view may have scrolled). Whether the top
-- row starts inside a comment is found by reading the rows above it.

local api = kilo.api
local ns = api.create_namespace('colour')

local function set(words)
  local t = {}
  for w in words:gmatch('%S+') do t[w] = true end
  return t
end

-- The languages: the names of their files, their comment marks, their
-- keywords (yellow) and types (green). C's lists are module 06's.
local LANGS = {
  {files = {'%.c$', '%.h$', '%.cpp$', '%.hpp$', '%.cc$'}, line = '//', open = '/*', close = '*/',
   keywords = set([[auto break case continue default do else enum extern for goto if
     register return sizeof static struct switch typedef union volatile while NULL
     alignas alignof and and_eq asm bitand bitor class compl constexpr const_cast
     decltype delete dynamic_cast explicit export false friend inline mutable
     namespace new noexcept not not_eq nullptr operator or or_eq private protected
     public reinterpret_cast static_assert static_cast template this thread_local
     throw true try typeid typename virtual xor xor_eq]]),
   types = set('int long double float char unsigned signed void short auto const bool')},
  {files = {'%.lua$'}, line = '--', open = '--[[', close = ']]',
   keywords = set([[and break do else elseif end for function goto if in local not
     or repeat return then until while]]),
   types = set('nil true false')},
}

local function language(name)
  for _, lang in ipairs(LANGS) do
    for _, pattern in ipairs(lang.files) do
      if name:match(pattern) then return lang end
    end
  end
end

-- Read one row, s, starting inside a comment or not; call paint(first,
-- last, style) for each span (bytes from 1, both included). Returns whether
-- the row ends inside a comment.
local function scan(s, lang, comment, paint)
  local i, n, sep, from = 1, #s, true, 1
  while i <= n do
    if comment then
      local e = s:find(lang.close, i, true)
      local stop = e and e + #lang.close - 1 or n
      paint(from, stop, 'cyan')
      i, comment, sep = stop + 1, e == nil, true
    elseif s:sub(i, i + #lang.open - 1) == lang.open then
      from, i, comment = i, i + #lang.open, true
    elseif s:sub(i, i + #lang.line - 1) == lang.line then
      paint(i, n, 'cyan')
      break
    else
      local ch = s:sub(i, i)
      if ch == '"' or ch == "'" then              -- a string: to the same quote
        local j = i + 1
        while j <= n and s:sub(j, j) ~= ch do
          if s:sub(j, j) == '\\' then j = j + 1 end
          j = j + 1
        end
        paint(i, math.min(j, n), 'magenta')
        i, sep = j + 1, false
      elseif sep and ch:match('%d') then          -- a number: digits and dots
        local j = s:match('^[%d%.]*()', i)
        paint(i, j - 1, 'red')
        i, sep = j, false
      elseif sep and ch:match('[%a_]') then       -- a word: a keyword, a type?
        local w = s:match('^[%a_][%w_]*', i)
        local style = lang.keywords[w] and 'yellow' or lang.types[w] and 'green'
        if style then paint(i, i + #w - 1, style) end
        i, sep = i + #w, false
      else
        sep = ch:match('[%s,%.%(%)%+%-/%*=~%%%[%];]') ~= nil
        i = i + 1
      end
    end
  end
  return comment
end

local function colour()
  api.clear_namespace(ns)
  local lang = language(api.get_name())
  if not lang then return end
  local top, rows = api.get_view()[1], api.get_size()[1]
  local count = api.line_count()
  local last = math.min(top + rows, count)
  local comment = false
  local none = function() end
  if top > 0 then
    for _, s in ipairs(api.get_lines(0, math.min(top, count))) do comment = scan(s, lang, comment, none) end
  end
  if last <= top then return end
  for i, s in ipairs(api.get_lines(top, last)) do
    local row = top + i - 1
    comment = scan(s, lang, comment, function(first, stop, style)
      api.add_highlight(ns, row, first - 1, stop, style)
    end)
  end
end

for _, event in ipairs({'BufReadPost', 'TextChanged', 'CursorMoved'}) do
  api.create_autocmd(event, colour)
end
colour()
return {colour = colour, scan = scan, language = language}
