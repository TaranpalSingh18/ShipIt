import React from "react";

const Signup = () => {
  return(
    <div className="flex flex-col items-center justify-center h-screen">
      <h1 className="text-2xl font-bold"> Signup</h1>
      <form className="flex flex-col gap-2 items-center justify-center">
        <input type="email" placeholder="Email" className="border-2 border-gray-300 rounded-md p-2" />
        <input type="password" placeholder="Password" className="border-2 border-gray-300 rounded-md p-2" />
        <button type="submit" className="bg-blue-500 text-white rounded-md p-2">Signup</button>
      </form>
    </div>
  )
}
export default Signup;