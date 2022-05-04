import { Stack } from '@fluentui/react';
import React from 'react';
import { Route, Routes } from 'react-router-dom';
import { Admin } from '../../App';
import { HomeDashboard } from './HomeDashboard';
import { LeftNav } from './LeftNav';

export const HomeLayout: React.FunctionComponent = () => {
  return (
    <>
      <Stack.Item className='tre-left-nav'>
        <LeftNav />
      </Stack.Item><Stack.Item className='tre-body-content'>
        <Routes>
          <Route path="/" element={<HomeDashboard />} />
          <Route path="/admin" element={<Admin />} />
        </Routes>
      </Stack.Item>
    </>
  );
};
