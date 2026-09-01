interface SearchInputProps {
  label: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
}

/** Controlled search box. Filtering happens in the feature provider, not here. */
export function SearchInput({ label, value, onChange, placeholder }: SearchInputProps) {
  return (
    <label className="search-input">
      {label}
      <input
        type="search"
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  )
}
