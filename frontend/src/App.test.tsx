import { render, screen } from '@testing-library/react'
import App from './App'

describe('App', () => {
  it('renders the getting-started heading', () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: /get started/i })).toBeInTheDocument()
  })

  it('renders the documentation section', () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: /documentation/i })).toBeInTheDocument()
  })
})
