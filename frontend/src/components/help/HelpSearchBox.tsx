import { Search, Sparkles, X } from 'lucide-react';
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { helpApi } from '@/lib/help-api';
import type { HelpSearchResult } from '@/lib/help-types';

export function HelpSearchBox({ initialQuery = '', autoFocus = false }: { initialQuery?: string; autoFocus?: boolean }) {
  return <SearchBox key={initialQuery} initialQuery={initialQuery} autoFocus={autoFocus} />;
}

function SearchBox({ initialQuery, autoFocus }: { initialQuery: string; autoFocus: boolean }) {
  const navigate = useNavigate();
  const [query, setQuery] = useState(initialQuery);
  const [response, setResponse] = useState<{ query: string; items: HelpSearchResult[] }>({ query: initialQuery, items: [] });
  const suggestions = response.query === query ? response.items : [];
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const [loadingQuery, setLoadingQuery] = useState<string | null>(null);
  const loading = loadingQuery === query && query.trim().length >= 2;
  const showSuggestions = open && response.query === query && query.trim().length >= 2;
  const generation = useRef(0);

  useEffect(() => {
    const value = query.trim();
    const current = ++generation.current;
    if (value.length < 2) return;
    const timer = window.setTimeout(() => {
      setLoadingQuery(query);
      void helpApi.search(value, undefined, 1, 6).then((result) => {
        if (current !== generation.current) return;
        setResponse({ query, items: result.items.slice(0, 6) }); setOpen(true); setActive(-1);
      }).catch(() => { if (current === generation.current) setResponse({ query, items: [] }); }).finally(() => { if (current === generation.current) setLoadingQuery(null); });
    }, 300);
    return () => { generation.current += 1; window.clearTimeout(timer); };
  }, [query]);

  function submit(event?: FormEvent) {
    event?.preventDefault(); const value = query.trim(); if (value.length < 2) return;
    setOpen(false); navigate(`/help/search?q=${encodeURIComponent(value)}`);
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Escape') { setOpen(false); return; }
    if (!showSuggestions || !suggestions.length) return;
    if (event.key === 'ArrowDown') { event.preventDefault(); setActive((value) => Math.min(suggestions.length - 1, value + 1)); }
    else if (event.key === 'ArrowUp') { event.preventDefault(); setActive((value) => Math.max(-1, value - 1)); }
    else if (event.key === 'Enter' && active >= 0) { event.preventDefault(); const item = suggestions[active]; if (item) { void helpApi.event('search_click', item.id, query.trim()); setOpen(false); navigate(`/help/articles/${item.slug}`); } }
  }

  return <div className="help-search-wrap">
    <form className="help-search" role="search" onSubmit={submit}>
      <Search aria-hidden="true" /><label className="sr-only" htmlFor="help-search-input">Search talktobot Help</label>
      <input type="search" id="help-search-input" autoFocus={autoFocus} value={query} onChange={(event) => setQuery(event.target.value)} onFocus={() => { if (suggestions.length) setOpen(true); }} onKeyDown={onKeyDown} placeholder="Search talktobot Help…" autoComplete="off" aria-autocomplete="list" aria-expanded={showSuggestions} aria-controls="help-search-suggestions" />
      {loading ? <span className="help-search__loading" aria-label="Searching" /> : query ? <button type="button" className="icon-button" aria-label="Clear search" onClick={() => { setQuery(''); setResponse({ query: '', items: [] }); setOpen(false); }}><X /></button> : null}
      <button type="submit" className="button button--primary button--md">Search</button>
    </form>
    <Link className="help-ask-link" to={`/help/ask${query.trim() ? `?q=${encodeURIComponent(query.trim())}` : ''}`}><Sparkles /> Ask Help AI</Link>
    {showSuggestions ? <div className="help-search__suggestions" id="help-search-suggestions" role="listbox">{suggestions.length ? suggestions.map((item, index) => <button key={item.id} type="button" role="option" aria-selected={index === active} className={index === active ? 'is-active' : ''} onMouseDown={(event) => event.preventDefault()} onClick={() => { void helpApi.event('search_click', item.id, query.trim()); setOpen(false); navigate(`/help/articles/${item.slug}`); }}><Search /><span><strong>{item.title}</strong><small>{item.categoryTitle}</small></span></button>) : <div className="help-search__no-suggestions">No direct matches. Press Search for more options.</div>}</div> : null}
  </div>;
}
