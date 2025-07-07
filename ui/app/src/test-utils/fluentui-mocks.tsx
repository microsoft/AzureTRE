import React from 'react';
import { vi } from 'vitest';

/**
 * Creates a mock Stack component with Item as a property.
 * Used across multiple FluentUI mocks to maintain consistency.
 */
export const createMockStack = () => {
  const MockStackComponent = ({ children, horizontal, style, styles, tokens, ...props }: any) => (
    <div
      data-testid="stack"
      data-horizontal={horizontal}
      style={style || styles?.root}
      {...props}
    >
      {children}
    </div>
  );

  MockStackComponent.Item = ({ children, align, grow, style, styles, ...props }: any) => (
    <div
      data-testid="stack-item"
      data-align={align}
      data-grow={grow}
      style={style || styles?.root}
      {...props}
    >
      {children}
    </div>
  );

  return MockStackComponent;
};

/**
 * Common FluentUI component mocks used across test files.
 * Provides consistent mock implementations with proper test attributes.
 */
export const createFluentUIMocks = () => ({
  // Common enums and utilities (these are frequently referenced)
  MessageBarType: {
    info: 'info',
    error: 'error',
    blocked: 'blocked',
    severeWarning: 'severeWarning',
    success: 'success',
    warning: 'warning',
    remove: 'remove',
  },

  PanelType: {
    smallFluid: 'smallFluid',
    smallFixedFar: 'smallFixedFar',
    smallFixedNear: 'smallFixedNear',
    medium: 'medium',
    large: 'large',
    largeFixed: 'largeFixed',
    extraLarge: 'extraLarge',
    custom: 'custom',
  },

  SpinnerSize: {
    xSmall: 'xSmall',
    small: 'small',
    medium: 'medium',
    large: 'large',
  },

  FontWeights: {
    light: 100,
    semilight: 200,
    regular: 400,
    semibold: 600,
    bold: 700,
  },

  DefaultPalette: {
    white: '#ffffff',
    black: '#000000',
    themePrimary: '#0078d4',
    neutralPrimary: '#323130',
    neutralDark: '#201f1e',
  },

  getTheme: () => ({
    fonts: {
      xxLarge: { fontSize: '24px' },
      xLarge: { fontSize: '20px' },
      large: { fontSize: '18px' },
      mediumPlus: { fontSize: '16px' },
      medium: { fontSize: '14px' },
      small: { fontSize: '12px' },
    },
    palette: {
      themePrimary: '#0078d4',
      neutralPrimary: '#323130',
      neutralDark: '#201f1e',
      white: '#ffffff',
    },
  }),

  mergeStyleSets: (styles: any) => styles,
  mergeStyles: (styles: any) => styles,

  // Dialog components
  Dialog: ({ children, hidden, onDismiss, dialogContentProps, modalProps, ...props }: any) =>
    !hidden ? (
      <div data-testid="dialog" role="dialog" {...props}>
        <div data-testid="dialog-title">{dialogContentProps?.title}</div>
        <div data-testid="dialog-subtext">{dialogContentProps?.subText}</div>
        <button data-testid="dialog-close" onClick={onDismiss}>
          X
        </button>
        {children}
      </div>
    ) : null,

  DialogFooter: ({ children, ...props }: any) => (
    <div data-testid="dialog-footer" {...props}>
      {children}
    </div>
  ),

  DialogType: {
    normal: "normal",
    largeHeader: "largeHeader",
    close: "close",
  },

  // Button components
  PrimaryButton: ({ text, children, iconProps, styles, onClick, disabled, primaryDisabled, ...props }: any) => (
    <button
      data-testid="primary-button"
      onClick={onClick}
      disabled={disabled || primaryDisabled}
      data-icon-name={iconProps?.iconName}
      style={styles?.root}
      {...props}
    >
      {text || children}
      {iconProps?.iconName && <span data-icon={iconProps.iconName}>{iconProps.iconName}</span>}
    </button>
  ),

  DefaultButton: ({ text, children, iconProps, styles, onClick, disabled, ...props }: any) => (
    <button
      data-testid="default-button"
      onClick={onClick}
      disabled={disabled}
      data-icon-name={iconProps?.iconName}
      style={styles?.root}
      {...props}
    >
      {text || children}
      {iconProps?.iconName && <span data-icon={iconProps.iconName}>{iconProps.iconName}</span>}
    </button>
  ),

  IconButton: ({ iconProps, onClick, styles, disabled, title, ...props }: any) => (
    <button
      data-testid="icon-button"
      data-icon-name={iconProps?.iconName}
      onClick={onClick}
      disabled={disabled}
      title={title}
      style={styles?.root}
      {...props}
    >
      {iconProps?.iconName}
    </button>
  ),

  // Form components
  TextField: ({
    readOnly,
    value,
    defaultValue,
    onChange,
    onKeyDown,
    placeholder,
    multiline,
    autoAdjustHeight,
    styles,
    label,
    errorMessage,
    ...props
  }: any) => (
    <div>
      {label && <label data-testid="text-field-label">{label}</label>}
      <input
        data-testid="text-field"
        readOnly={readOnly}
        value={value}
        defaultValue={defaultValue}
        onChange={onChange}
        onKeyDown={onKeyDown}
        placeholder={placeholder}
        style={styles?.field || styles?.root}
        {...props}
      />
      {errorMessage && <div data-testid="text-field-error">{errorMessage}</div>}
    </div>
  ),

  Dropdown: ({
    options,
    selectedKey,
    onChange,
    placeholder,
    label,
    disabled,
    styles,
    ...props
  }: any) => (
    <div>
      {label && <label data-testid="dropdown-label">{label}</label>}
      <select
        data-testid="dropdown"
        value={selectedKey}
        onChange={(e) => onChange?.(e, { key: e.target.value, text: e.target.options[e.target.selectedIndex]?.text })}
        disabled={disabled}
        style={styles?.dropdown || styles?.root}
        {...props}
      >
        {placeholder && <option value="">{placeholder}</option>}
        {options?.map((option: any) => (
          <option key={option.key} value={option.key}>
            {option.text}
          </option>
        ))}
      </select>
    </div>
  ),

  Checkbox: ({ label, checked, onChange, disabled, styles, ...props }: any) => (
    <label data-testid="checkbox-label" style={styles?.root}>
      <input
        data-testid="checkbox"
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange?.(e, e.target.checked)}
        disabled={disabled}
        {...props}
      />
      {label}
    </label>
  ),

  // Layout components
  Stack: createMockStack(),

  // Display components
  Text: ({ children, variant, styles, ...props }: any) => (
    <span data-testid="text" data-variant={variant} style={styles?.root} {...props}>
      {children}
    </span>
  ),

  Label: ({ children, required, styles, ...props }: any) => (
    <label data-testid="label" data-required={required} style={styles?.root} {...props}>
      {children}
    </label>
  ),

  Link: ({ children, onClick, href, title, style, disabled, ...props }: any) => (
    <a
      data-testid="fluent-link"
      onClick={disabled ? undefined : onClick}
      href={disabled ? undefined : href}
      title={title}
      style={style}
      data-disabled={disabled}
      {...props}
    >
      {children}
    </a>
  ),

  Icon: ({ iconName, styles, ...props }: any) => (
    <span data-testid="icon" data-icon-name={iconName} style={styles?.root} {...props}>
      {iconName}
    </span>
  ),

  // Feedback components
  MessageBar: ({
    children,
    messageBarType,
    isMultiline,
    onDismiss,
    dismissButtonAriaLabel,
    styles,
    ...props
  }: any) => (
    <div
      data-testid="message-bar"
      data-type={messageBarType}
      data-multiline={isMultiline}
      style={styles?.root}
      {...props}
    >
      {children}
      {onDismiss && (
        <button
          data-testid="dismiss-button"
          onClick={onDismiss}
          aria-label={dismissButtonAriaLabel}
        >
          X
        </button>
      )}
    </div>
  ),

  Spinner: ({ label, size, styles, ...props }: any) => (
    <div
      data-testid="spinner"
      role="progressbar"
      data-size={size}
      style={styles?.root}
      {...props}
    >
      {label}
    </div>
  ),

  FontIcon: ({ iconName, className, style, ...props }: any) => (
    <i
      data-testid="font-icon"
      data-icon-name={iconName}
      className={className}
      style={style}
      {...props}
    />
  ),

  ProgressIndicator: ({
    label,
    description,
    percentComplete,
    progressHidden,
    styles,
    ...props
  }: any) => (
    <div data-testid="progress-indicator" style={styles?.root} {...props}>
      {label && <div data-testid="progress-label">{label}</div>}
      {description && <div data-testid="progress-description">{description}</div>}
      {!progressHidden && (
        <div data-testid="progress-bar" data-percent={percentComplete} />
      )}
    </div>
  ),

  // Overlay components
  TooltipHost: ({ content, children, styles, ...props }: any) => (
    <div data-testid="tooltip-host" title={content} style={styles?.root} {...props}>
      {children}
    </div>
  ),

  Modal: ({ isOpen, children, onDismiss, isBlocking, titleAriaId, styles, ...props }: any) =>
    isOpen ? (
      <div
        data-testid="modal"
        role="dialog"
        aria-modal={isBlocking}
        aria-labelledby={titleAriaId}
        style={styles?.root}
        {...props}
      >
        {children}
        {onDismiss && (
          <button
            data-testid="modal-close"
            onClick={onDismiss}
            aria-label="Close popup modal"
          >
            X
          </button>
        )}
      </div>
    ) : null,

  Callout: ({ children, target, onDismiss, hidden, styles, ...props }: any) =>
    !hidden ? (
      <div data-testid="callout" style={styles?.root} {...props}>
        {children}
        {onDismiss && (
          <button data-testid="callout-close" onClick={onDismiss}>
            X
          </button>
        )}
      </div>
    ) : null,

  // Navigation components
  Nav: ({ groups, styles, ...props }: any) => (
    <nav data-testid="nav" style={styles?.root} {...props}>
      {groups?.map((group: any, groupIndex: number) => (
        <div key={groupIndex} data-testid="nav-group">
          {group.name && <div data-testid="nav-group-name">{group.name}</div>}
          {group.links?.map((link: any, linkIndex: number) => (
            <a
              key={linkIndex}
              data-testid="nav-link"
              href={link.url}
              onClick={link.onClick}
              data-key={link.key}
            >
              {link.name}
            </a>
          ))}
        </div>
      ))}
    </nav>
  ),

  // Data components
  DetailsList: ({
    items,
    columns,
    onRenderItemColumn,
    selection,
    selectionMode,
    styles,
    ...props
  }: any) => (
    <div data-testid="details-list" style={styles?.root} {...props}>
      <table>
        <thead>
          <tr>
            {columns?.map((column: any) => (
              <th key={column.key} data-testid="details-list-header">
                {column.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items?.map((item: any, index: number) => (
            <tr key={index} data-testid="details-list-row">
              {columns?.map((column: any) => (
                <td key={column.key} data-testid="details-list-cell">
                  {onRenderItemColumn ? onRenderItemColumn(item, index, column) : item[column.fieldName || column.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  ),

  // Other commonly used components
  Separator: ({ styles, ...props }: any) => (
    <hr data-testid="separator" style={styles?.root} {...props} />
  ),

  Panel: ({
    isOpen,
    onDismiss,
    headerText,
    children,
    styles,
    ...props
  }: any) =>
    isOpen ? (
      <div data-testid="panel" style={styles?.root} {...props}>
        <div data-testid="panel-header">
          {headerText}
          <button data-testid="panel-close" onClick={onDismiss}>
            X
          </button>
        </div>
        <div data-testid="panel-content">{children}</div>
      </div>
    ) : null,
});

/**
 * Creates a complete FluentUI mock with all common components.
 * Use this in vi.mock("@fluentui/react") calls.
 *
 * @example
 * vi.mock("@fluentui/react", async () => {
 *   const actual = await vi.importActual("@fluentui/react");
 *   return {
 *     ...actual,
 *     ...createCompleteFluentUIMock(),
 *   };
 * });
 */
export const createCompleteFluentUIMock = () => {
  return createFluentUIMocks();
};

/**
 * Creates a partial FluentUI mock with only specific components.
 * Useful when you only need to mock certain components.
 * Always includes common enums and utilities (MessageBarType, PanelType, etc.)
 *
 * @param componentNames - Array of component names to include in the mock
 * @example
 * vi.mock("@fluentui/react", async () => {
 *   const actual = await vi.importActual("@fluentui/react");
 *   return {
 *     ...actual,
 *     ...createPartialFluentUIMock(['Dialog', 'PrimaryButton', 'TextField']),
 *   };
 * });
 */
export const createPartialFluentUIMock = (componentNames: string[]) => {
  const allMocks = createFluentUIMocks();
  const partialMocks: any = {};

  // Always include common enums and utilities
  const alwaysInclude = [
    'MessageBarType', 'PanelType', 'SpinnerSize', 'FontWeights', 'DefaultPalette',
    'getTheme', 'mergeStyleSets', 'mergeStyles'
  ];

  [...alwaysInclude, ...componentNames].forEach(name => {
    if (allMocks[name as keyof typeof allMocks]) {
      partialMocks[name] = allMocks[name as keyof typeof allMocks];
    }
  });

  return partialMocks;
};

/**
 * Mock clipboard API for testing copy functionality.
 * Call this in your test setup or individual test files.
 */
export const mockClipboardAPI = () => {
  Object.assign(navigator, {
    clipboard: {
      writeText: vi.fn(() => Promise.resolve()),
      readText: vi.fn(() => Promise.resolve('')),
    },
  });
};
