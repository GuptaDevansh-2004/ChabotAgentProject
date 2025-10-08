declare module 'redux-persist/integration/react' {
  import * as React from 'react';
  import type { Persistor } from 'redux-persist/es/types';

  export interface PersistGateProps {
    persistor: Persistor;
    loading?: React.ReactNode;
    onBeforeLift?: () => void | Promise<void>;
    children: React.ReactNode | ((bootstrapped: boolean) => React.ReactNode);
  }

  export class PersistGate extends React.PureComponent<PersistGateProps> {}
}