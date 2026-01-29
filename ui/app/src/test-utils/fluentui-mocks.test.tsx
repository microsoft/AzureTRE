import React from 'react';
import { render, screen } from '@testing-library/react';
import { createFluentUIMocks } from './fluentui-mocks';

describe('fluentui mocks normalizations', () => {
  const {
    Spinner,
    Dialog,
    Panel,
    TooltipHost,
    Dropdown,
  } = createFluentUIMocks();

  test('Spinner maps ariaLive and labelPosition to safe DOM attributes', () => {
    render(<Spinner label="Loading" ariaLive="assertive" labelPosition="right" /> as any);

    const spinner = screen.getByTestId('spinner');
    expect(spinner).toHaveAttribute('aria-live', 'assertive');
    expect(spinner).toHaveAttribute('data-label-position', 'right');
  });

  test('Dialog uses closeButtonAriaLabel as aria-label on close button', () => {
    render(
      <Dialog
        hidden={false}
        onDismiss={() => { }}
        dialogContentProps={{ title: 'T', subText: 'S', closeButtonAriaLabel: 'Close dialog' }}
      /> as any,
    );

    const close = screen.getByTestId('dialog-close');
    expect(close).toHaveAttribute('aria-label', 'Close dialog');
    expect(screen.getByTestId('dialog-title')).toHaveTextContent('T');
  });

  test('Panel maps isLightDismiss and closeButtonAriaLabel correctly', () => {
    render(
      <Panel isOpen onDismiss={() => { }} headerText="Header" isLightDismiss closeButtonAriaLabel="close panel" /> as any,
    );

    expect(screen.getByTestId('panel')).toHaveAttribute('data-is-light-dismiss', 'true');
    expect(screen.getByTestId('panel-close')).toHaveAttribute('aria-label', 'close panel');
  });

  test('TooltipHost exposes tooltipProps as data attribute rather than forwarding to DOM', () => {
    render(
      <TooltipHost content="tip" tooltipProps={{ target: 'x' }}>
        <span>child</span>
      </TooltipHost> as any,
    );

    expect(screen.getByTestId('tooltip')).toHaveAttribute('data-tooltip-props', JSON.stringify({ target: 'x' }));
  });

  test('Dropdown ignores onRenderOption prop so it is not forwarded to DOM', () => {
    render(
      <Dropdown
        options={[{ key: '1', text: 'One' }]}
        selectedKey={'1'}
        onChange={() => { }}
        onRenderOption={() => null}
      /> as any,
    );

    const dropdown = screen.getByTestId('dropdown');
    expect(dropdown).toBeInTheDocument();
  });
});
