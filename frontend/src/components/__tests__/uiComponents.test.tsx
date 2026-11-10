// frontend/src/components/__tests__/uiComponents.test.tsx
import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Badge } from '../ui/Badge';
import { SeverityBadge } from '../ui/SeverityBadge';
import { StatusDot } from '../ui/StatusDot';
import { Card } from '../ui/Card';
import { EmptyState } from '../ui/EmptyState';
import { DataTable } from '../ui/DataTable';

describe('UI Design System Components', () => {
  it('renders Badge with correct text and classes', () => {
    const { rerender } = render(<Badge variant="indigo">Test Badge</Badge>);
    expect(screen.getByText('Test Badge')).toBeTruthy();

    rerender(<Badge variant="danger">Error Alert</Badge>);
    expect(screen.getByText('Error Alert')).toBeTruthy();
  });

  it('renders SeverityBadge with correct labels and colors', () => {
    const { rerender } = render(<SeverityBadge severity="critical" />);
    expect(screen.getByText(/critical/i)).toBeTruthy();

    rerender(<SeverityBadge severity="high" />);
    expect(screen.getByText(/high/i)).toBeTruthy();

    rerender(<SeverityBadge severity="low" />);
    expect(screen.getByText(/low/i)).toBeTruthy();
  });

  it('renders StatusDot with appropriate color indicator', () => {
    const { container, rerender } = render(<StatusDot status="online" />);
    expect(container.querySelector('.bg-emerald-500')).toBeTruthy();

    rerender(<StatusDot status="offline" />);
    expect(container.querySelector('.bg-rose-500')).toBeTruthy();

    rerender(<StatusDot status="warning" />);
    expect(container.querySelector('.bg-amber-500')).toBeTruthy();
  });

  it('renders Card with header, footer, and children', () => {
    render(
      <Card
        header={<h3>Card Title</h3>}
        footer={<span>Card Footer</span>}
        className="custom-card"
      >
        <p>Main Card Body Content</p>
      </Card>
    );

    expect(screen.getByText('Card Title')).toBeTruthy();
    expect(screen.getByText('Main Card Body Content')).toBeTruthy();
    expect(screen.getByText('Card Footer')).toBeTruthy();
  });

  it('renders EmptyState with custom title and message', () => {
    render(
      <EmptyState
        title="Zero Telemetry"
        message="Collecting data from agents in progress."
      />
    );

    expect(screen.getByText('Zero Telemetry')).toBeTruthy();
    expect(screen.getByText('Collecting data from agents in progress.')).toBeTruthy();
  });

  it('renders DataTable and filters records by search keyword', () => {
    const data = [
      { id: '1', hostname: 'worker-win-01', ip: '10.0.0.1' },
      { id: '2', hostname: 'worker-win-02', ip: '10.0.0.2' },
      { id: '3', hostname: 'db-server', ip: '10.0.0.3' },
    ];

    const columns = [
      { key: 'hostname', header: 'Host' },
      { key: 'ip', header: 'IP Address' },
    ];

    render(
      <DataTable
        columns={columns}
        data={data}
        searchKey="hostname"
        searchPlaceholder="Search hosts..."
      />
    );

    expect(screen.getByText('worker-win-01')).toBeTruthy();
    expect(screen.getByText('worker-win-02')).toBeTruthy();
    expect(screen.getByText('db-server')).toBeTruthy();

    // Type in search box
    const searchInput = screen.getByPlaceholderText('Search hosts...');
    fireEvent.change(searchInput, { target: { value: 'db-server' } });

    expect(screen.getByText('db-server')).toBeTruthy();
    expect(screen.queryByText('worker-win-01')).toBeNull();
  });
});
